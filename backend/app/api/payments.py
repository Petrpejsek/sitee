"""Payment endpoints for Stripe integration"""
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import stripe

from app.database import get_db
from app.models import (
    User, AuditJob, Payment, Subscription, 
    PaymentType, PaymentStatus, SubscriptionPlan, SubscriptionStatus,
    AuditAccessState
)
from app.config import get_settings
from app.api.auth import get_current_user_id
from app.services.analytics import AnalyticsService
from app.services.access_control import AccessControlService

router = APIRouter(prefix="/payments", tags=["payments"])
settings = get_settings()

# Initialize Stripe
stripe.api_key = settings.stripe_api_key


class CreateAuditCheckoutRequest(BaseModel):
    """Request to create audit payment checkout"""
    audit_id: UUID


class CreateSubscriptionCheckoutRequest(BaseModel):
    """Request to create subscription checkout"""
    plan: SubscriptionPlan
    audit_id: Optional[UUID] = None  # Optional: audit to unlock after subscription


class CheckoutSessionResponse(BaseModel):
    """Checkout session response"""
    session_id: str
    url: str


@router.post("/create-audit-checkout", response_model=CheckoutSessionResponse)
async def create_audit_checkout(
    request: CreateAuditCheckoutRequest,
    user_id: Optional[UUID] = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Create Stripe checkout session for $199 audit payment
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Verify audit exists
    result = await db.execute(
        select(AuditJob).where(AuditJob.id == request.audit_id)
    )
    audit = result.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    
    # Check if already paid
    access_control = AccessControlService(db)
    if await access_control.has_paid_for_audit(user_id, request.audit_id):
        raise HTTPException(status_code=400, detail="Audit already unlocked")
    
    # Get user
    user = await access_control.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create payment record
    payment = Payment(
        id=uuid.uuid4(),
        user_id=user_id,
        audit_id=request.audit_id,
        payment_type=PaymentType.AUDIT,
        amount=19900,  # $199.00 in cents
        currency="usd",
        status=PaymentStatus.PENDING,
        created_at=datetime.utcnow()
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    
    # Create Stripe checkout session
    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email=user.email,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": settings.stripe_audit_price_id,
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=f"{settings.frontend_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.frontend_url}/report/{request.audit_id}",
            metadata={
                "payment_id": str(payment.id),
                "user_id": str(user_id),
                "audit_id": str(request.audit_id),
                "payment_type": "audit"
            }
        )
        
        # Store session ID
        payment.stripe_checkout_session_id = checkout_session.id
        await db.commit()
        
        # Track analytics
        analytics = AnalyticsService(db)
        await analytics.track_unlock_clicked(user_id, request.audit_id)
        
        return CheckoutSessionResponse(
            session_id=checkout_session.id,
            url=checkout_session.url
        )
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")


@router.post("/create-subscription-checkout", response_model=CheckoutSessionResponse)
async def create_subscription_checkout(
    request: CreateSubscriptionCheckoutRequest,
    user_id: Optional[UUID] = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Create Stripe checkout session for subscription
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Check if already subscribed
    access_control = AccessControlService(db)
    if await access_control.has_active_subscription(user_id):
        raise HTTPException(status_code=400, detail="Already subscribed")
    
    # Get user
    user = await access_control.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Map plan to Stripe price ID
    price_id_map = {
        SubscriptionPlan.STARTER: settings.stripe_starter_price_id,
        SubscriptionPlan.GROWTH: settings.stripe_growth_price_id,
        SubscriptionPlan.SCALE: settings.stripe_scale_price_id
    }
    price_id = price_id_map.get(request.plan)
    if not price_id:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    # Create Stripe checkout session
    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email=user.email,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            mode="subscription",
            success_url=f"{settings.frontend_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.frontend_url}/report/{request.audit_id}" if request.audit_id else f"{settings.frontend_url}",
            metadata={
                "user_id": str(user_id),
                "plan": request.plan.value,
                "payment_type": "subscription",
                "audit_id": str(request.audit_id) if request.audit_id else None
            }
        )
        
        return CheckoutSessionResponse(
            session_id=checkout_session.id,
            url=checkout_session.url
        )
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")


@router.get("/verify-session")
async def verify_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify Stripe checkout session and return payment status
    """
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        
        return {
            "status": session.payment_status,
            "customer_email": session.customer_details.email if session.customer_details else None,
            "amount_total": session.amount_total,
            "metadata": session.metadata
        }
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Stripe webhook events
    
    Events handled:
    - checkout.session.completed: Payment succeeded
    - customer.subscription.updated: Subscription changed
    - customer.subscription.deleted: Subscription canceled
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    analytics = AnalyticsService(db)
    access_control = AccessControlService(db)
    
    # Handle checkout.session.completed
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        payment_type = metadata.get("payment_type")
        
        if payment_type == "audit":
            # Handle one-time audit payment
            payment_id = metadata.get("payment_id")
            user_id = UUID(metadata.get("user_id"))
            audit_id = UUID(metadata.get("audit_id"))
            
            # Update payment status
            result = await db.execute(
                select(Payment).where(Payment.id == UUID(payment_id))
            )
            payment = result.scalar_one_or_none()
            if payment:
                payment.status = PaymentStatus.COMPLETED
                payment.completed_at = datetime.utcnow()
                payment.stripe_payment_intent_id = session.get("payment_intent")
                await db.commit()
            
            # Unlock audit
            await access_control.unlock_audit_for_user(user_id, audit_id)
            
            # Track analytics
            await analytics.track_audit_paid(
                user_id, audit_id, 19900, session.get("id")
            )
        
        elif payment_type == "subscription":
            # Handle subscription creation
            user_id = UUID(metadata.get("user_id"))
            plan = metadata.get("plan")
            subscription_id = session.get("subscription")
            customer_id = session.get("customer")
            
            # Create subscription record
            subscription = Subscription(
                id=uuid.uuid4(),
                user_id=user_id,
                stripe_subscription_id=subscription_id,
                stripe_customer_id=customer_id,
                plan=SubscriptionPlan(plan),
                status=SubscriptionStatus.ACTIVE,
                started_at=datetime.utcnow(),
                current_period_end=datetime.fromtimestamp(session.get("subscription_data", {}).get("current_period_end", 0))
            )
            db.add(subscription)
            await db.commit()
            
            # Unlock all user audits
            await access_control.unlock_all_audits_for_subscriber(user_id)
            
            # Track analytics
            await analytics.track_subscription_started(
                user_id, plan, subscription_id
            )
    
    # Handle subscription updates
    elif event["type"] == "customer.subscription.updated":
        subscription_data = event["data"]["object"]
        stripe_subscription_id = subscription_data.get("id")
        
        result = await db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id)
        )
        subscription = result.scalar_one_or_none()
        if subscription:
            subscription.current_period_end = datetime.fromtimestamp(subscription_data.get("current_period_end"))
            subscription.status = SubscriptionStatus(subscription_data.get("status"))
            await db.commit()
    
    # Handle subscription deletion
    elif event["type"] == "customer.subscription.deleted":
        subscription_data = event["data"]["object"]
        stripe_subscription_id = subscription_data.get("id")
        
        result = await db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id)
        )
        subscription = result.scalar_one_or_none()
        if subscription:
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = datetime.utcnow()
            await db.commit()
    
    return {"success": True}
