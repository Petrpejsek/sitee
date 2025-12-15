"""Access control service for audit paywall system"""
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User, AuditJob, Payment, Subscription, AuditAccessState, PaymentStatus, SubscriptionStatus, PaymentType


class AccessControlService:
    """Service for determining user and audit access states"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def has_paid_for_audit(self, user_id: UUID, audit_id: UUID) -> bool:
        """Check if user has paid for specific audit"""
        result = await self.db.execute(
            select(Payment).where(
                Payment.user_id == user_id,
                Payment.audit_id == audit_id,
                Payment.payment_type == PaymentType.AUDIT,
                Payment.status == PaymentStatus.COMPLETED
            )
        )
        payment = result.scalar_one_or_none()
        return payment is not None
    
    async def has_active_subscription(self, user_id: UUID) -> bool:
        """Check if user has active subscription"""
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE
            )
        )
        subscription = result.scalar_one_or_none()
        return subscription is not None
    
    async def get_audit_access_state(
        self, 
        user_id: Optional[UUID], 
        audit_id: UUID
    ) -> AuditAccessState:
        """
        Determine audit access state based on user and payment status
        
        Rules:
        - No user (anonymous) -> PREVIEW
        - Has active subscription -> UNLOCKED
        - Has paid for this specific audit -> UNLOCKED
        - Registered but not paid -> LOCKED
        """
        # Anonymous users get preview
        if not user_id:
            return AuditAccessState.PREVIEW
        
        # Check if user exists
        user = await self.get_user_by_id(user_id)
        if not user:
            return AuditAccessState.PREVIEW
        
        # Check for active subscription (unlocks all audits)
        if await self.has_active_subscription(user_id):
            return AuditAccessState.UNLOCKED
        
        # Check if paid for this specific audit
        if await self.has_paid_for_audit(user_id, audit_id):
            return AuditAccessState.UNLOCKED
        
        # Registered but not paid -> locked
        return AuditAccessState.LOCKED
    
    async def update_audit_access_state(
        self, 
        audit_id: UUID, 
        access_state: AuditAccessState
    ) -> None:
        """Update audit access state in database"""
        result = await self.db.execute(
            select(AuditJob).where(AuditJob.id == audit_id)
        )
        audit = result.scalar_one_or_none()
        if audit:
            audit.audit_access_state = access_state
            await self.db.commit()
    
    async def unlock_audit_for_user(self, user_id: UUID, audit_id: UUID) -> None:
        """Unlock specific audit for user"""
        result = await self.db.execute(
            select(AuditJob).where(AuditJob.id == audit_id)
        )
        audit = result.scalar_one_or_none()
        if audit:
            audit.audit_access_state = AuditAccessState.UNLOCKED
            if not audit.user_id:
                audit.user_id = user_id
            await self.db.commit()
    
    async def unlock_all_audits_for_subscriber(self, user_id: UUID) -> None:
        """Unlock all audits for user who just became a subscriber"""
        result = await self.db.execute(
            select(AuditJob).where(AuditJob.user_id == user_id)
        )
        audits = result.scalars().all()
        for audit in audits:
            audit.audit_access_state = AuditAccessState.UNLOCKED
        await self.db.commit()
    
    @staticmethod
    def can_view_section_6(access_state: AuditAccessState) -> bool:
        """Determine if Section 6 should be visible"""
        return access_state == AuditAccessState.UNLOCKED
    
    @staticmethod
    def get_locked_sections(access_state: AuditAccessState) -> list[str]:
        """
        Get list of sections that should be locked based on access state
        
        For LOCKED state: User sees 20-30% content (teaser), 70-80% is locked
        The backend filters the DATA, this list tells frontend WHERE to show overlays
        
        Returns section IDs that should have lock overlays
        """
        if access_state == AuditAccessState.PREVIEW:
            # Preview (anonymous): Most sections locked
            return [
                "section_2_details",  # Company intel details
                "section_3_details",  # Decision audit details  
                "section_4",          # Requirements
                "section_5",          # Roadmap
                "section_6",          # Growth plan
                "recommendations",    # All "how to fix" content
                "checklists",         # Detailed checklists
            ]
        elif access_state == AuditAccessState.LOCKED:
            # Locked (registered but not paid): 
            # Show score + top problems (names only) + section titles
            # Lock ALL detailed content, recommendations, steps, fixes
            return [
                "section_2_details",  # Company intel deep analysis
                "section_3_details",  # Decision audit recommendations
                "section_4",          # AI requirements details
                "section_5",          # Roadmap / what to do
                "section_6",          # Growth plan - completely locked
                "recommendations",    # All recommendation text
                "checklists",         # Detailed checklists
                "gap_details",        # Gap explanations and fixes
                "risk_details",       # Risk analysis and mitigations
                "action_items",       # Specific action items
            ]
        else:
            # Unlocked: Show everything
            return []
