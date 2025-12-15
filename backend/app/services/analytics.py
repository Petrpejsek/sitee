"""Analytics event tracking service"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from app.database import Base


class AnalyticsEvent(Base):
    """Analytics event model"""
    __tablename__ = "analytics_events"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False, index=True)
    user_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)
    audit_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)
    event_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class AnalyticsService:
    """Service for tracking analytics events"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def track_event(
        self,
        event_type: str,
        user_id: Optional[UUID] = None,
        audit_id: Optional[UUID] = None,
        event_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track an analytics event
        
        Event types:
        - audit_started: When user initiates an audit
        - email_submitted: When user provides email
        - unlock_clicked: When user clicks unlock CTA
        - unlock_modal_opened: When unlock modal is shown
        - audit_paid: When user completes audit payment
        - subscription_started: When user starts subscription
        - magic_link_sent: When magic link email is sent
        - magic_link_verified: When user clicks magic link
        """
        event = AnalyticsEvent(
            event_type=event_type,
            user_id=user_id,
            audit_id=audit_id,
            event_data=event_data or {},
            created_at=datetime.utcnow()
        )
        self.db.add(event)
        try:
            await self.db.commit()
        except Exception as e:
            # Don't fail the request if analytics fails
            await self.db.rollback()
            print(f"Analytics tracking failed: {e}")
    
    async def track_audit_started(self, domain: str, audit_id: UUID) -> None:
        """Track when an audit is started"""
        await self.track_event(
            event_type="audit_started",
            audit_id=audit_id,
            event_data={"domain": domain}
        )
    
    async def track_email_submitted(self, user_id: UUID, audit_id: UUID, email: str) -> None:
        """Track when user submits email"""
        await self.track_event(
            event_type="email_submitted",
            user_id=user_id,
            audit_id=audit_id,
            event_data={"email": email}
        )
    
    async def track_unlock_clicked(self, user_id: UUID, audit_id: UUID) -> None:
        """Track when user clicks unlock button"""
        await self.track_event(
            event_type="unlock_clicked",
            user_id=user_id,
            audit_id=audit_id
        )
    
    async def track_unlock_modal_opened(self, user_id: UUID, audit_id: UUID) -> None:
        """Track when unlock modal is opened"""
        await self.track_event(
            event_type="unlock_modal_opened",
            user_id=user_id,
            audit_id=audit_id
        )
    
    async def track_audit_paid(
        self, 
        user_id: UUID, 
        audit_id: UUID, 
        amount: int, 
        stripe_session_id: str
    ) -> None:
        """Track when audit payment is completed"""
        await self.track_event(
            event_type="audit_paid",
            user_id=user_id,
            audit_id=audit_id,
            event_data={
                "amount": amount,
                "currency": "usd",
                "stripe_session_id": stripe_session_id
            }
        )
    
    async def track_subscription_started(
        self, 
        user_id: UUID, 
        plan: str, 
        stripe_subscription_id: str
    ) -> None:
        """Track when subscription is started"""
        await self.track_event(
            event_type="subscription_started",
            user_id=user_id,
            event_data={
                "plan": plan,
                "stripe_subscription_id": stripe_subscription_id
            }
        )
    
    async def track_magic_link_sent(self, user_id: UUID, email: str) -> None:
        """Track when magic link is sent"""
        await self.track_event(
            event_type="magic_link_sent",
            user_id=user_id,
            event_data={"email": email}
        )
    
    async def track_magic_link_verified(self, user_id: UUID, audit_id: Optional[UUID] = None) -> None:
        """Track when user verifies magic link"""
        await self.track_event(
            event_type="magic_link_verified",
            user_id=user_id,
            audit_id=audit_id
        )
