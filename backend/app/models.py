"""SQLAlchemy database models"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class UserState(str, enum.Enum):
    """User state enum"""
    ANON = "anon"
    REGISTERED = "registered"
    PAID_AUDIT = "paid_audit"
    SUBSCRIBER = "subscriber"


class AuditAccessState(str, enum.Enum):
    """Audit access state enum"""
    PREVIEW = "preview"
    LOCKED = "locked"
    UNLOCKED = "unlocked"


class PaymentType(str, enum.Enum):
    """Payment type enum"""
    AUDIT = "audit"
    SUBSCRIPTION = "subscription"


class PaymentStatus(str, enum.Enum):
    """Payment status enum"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class SubscriptionPlan(str, enum.Enum):
    """Subscription plan enum"""
    STARTER = "starter"
    GROWTH = "growth"
    SCALE = "scale"


class SubscriptionStatus(str, enum.Enum):
    """Subscription status enum"""
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"


class User(Base):
    """User model for authentication and access control"""
    __tablename__ = "users"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Magic link authentication
    magic_link_token = Column(String(255), nullable=True, index=True)
    magic_link_expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    audits = relationship("AuditJob", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    subscription = relationship("Subscription", back_populates="user", uselist=False)


class AuditJob(Base):
    """Audit job model"""
    __tablename__ = "audit_jobs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # User relationship (nullable for backward compatibility)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Access control
    audit_access_state = Column(SQLEnum(AuditAccessState), nullable=False, default=AuditAccessState.PREVIEW)
    
    # Input data
    target_domain = Column(String(255), nullable=False)
    competitor_domains = Column(JSONB, default=list)
    locale = Column(String(10), nullable=False)
    company_description = Column(Text)
    products_services = Column(Text)
    
    # Job status
    status = Column(String(50), nullable=False, default="pending")
    current_stage = Column(String(50))
    progress_percent = Column(Integer, default=0)
    error_message = Column(Text)
    
    # Outputs
    audit_result = Column(JSONB)
    report_pdf_path = Column(String(500))
    report_html_path = Column(String(500))
    
    # Metadata
    scraping_started_at = Column(DateTime)
    scraping_completed_at = Column(DateTime)
    llm_started_at = Column(DateTime)
    llm_completed_at = Column(DateTime)
    report_generated_at = Column(DateTime)
    total_pages_scraped = Column(Integer, default=0)
    
    # Debug info for scraping failures
    scrape_debug = Column(JSONB)
    
    # Relationships
    user = relationship("User", back_populates="audits")
    scraped_pages = relationship("ScrapedPage", back_populates="audit_job", cascade="all, delete-orphan")
    output = relationship("AuditOutput", back_populates="audit_job", uselist=False, cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="audit")


class ScrapedPage(Base):
    """Scraped page model"""
    __tablename__ = "scraped_pages"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_job_id = Column(UUID(as_uuid=True), ForeignKey("audit_jobs.id", ondelete="CASCADE"), nullable=False)
    
    # URL info
    url = Column(Text, nullable=False)
    domain = Column(String(255), nullable=False)
    is_target = Column(Boolean, default=True)
    
    # Content
    html_content = Column(Text)
    text_content = Column(Text)
    title = Column(String(500))
    meta_description = Column(Text)
    
    # Metadata
    scraped_at = Column(DateTime, default=datetime.utcnow)
    status_code = Column(Integer)
    content_type = Column(String(100))
    word_count = Column(Integer)
    
    # Dedup
    url_hash = Column(String(64), unique=True)
    
    # Relationships
    audit_job = relationship("AuditJob", back_populates="scraped_pages")


class AuditOutput(Base):
    """Audit output storage - single source of truth for results"""
    __tablename__ = "audit_outputs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_job_id = Column(UUID(as_uuid=True), ForeignKey("audit_jobs.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Stage A: Core Audit data
    audit_json = Column(JSONB, nullable=False)
    
    # Stage B: Action Plan data
    action_plan_json = Column(JSONB)  # Stage B output - pages, outlines, impact forecast
    
    # Report output
    report_html = Column(Text)
    
    # File references
    pdf_path = Column(String(500))
    pdf_blob = Column(Text)  # Base64 if needed for cloud storage
    
    # Metadata
    model = Column(String(50), nullable=False)  # e.g., "gpt-4o"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    run_id = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    
    # Sampling info
    sampled_urls = Column(JSONB)  # List of URLs actually analyzed
    
    # Relationships
    audit_job = relationship("AuditJob", back_populates="output")


class AuditOutputSnapshot(Base):
    """
    Historical snapshot of an AuditOutput.
    Used for retention UI ("change since last run") without changing the dashboard layout.
    """
    __tablename__ = "audit_output_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_job_id = Column(UUID(as_uuid=True), ForeignKey("audit_jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    # Snapshot payload (same shape as AuditOutput)
    audit_json = Column(JSONB, nullable=False)
    action_plan_json = Column(JSONB)
    sampled_urls = Column(JSONB)

    # Metadata
    model = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    run_id = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)

    # Relationship
    audit_job = relationship("AuditJob")


class Payment(Base):
    """Payment model for audit purchases and subscriptions"""
    __tablename__ = "payments"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audit_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Payment details
    payment_type = Column(SQLEnum(PaymentType), nullable=False)
    amount = Column(Integer, nullable=False)  # Amount in cents
    currency = Column(String(3), nullable=False, default="usd")
    status = Column(SQLEnum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    
    # Stripe references
    stripe_payment_intent_id = Column(String(255), nullable=True, index=True)
    stripe_checkout_session_id = Column(String(255), nullable=True, unique=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="payments")
    audit = relationship("AuditJob", back_populates="payments")


class Subscription(Base):
    """Subscription model for recurring plans"""
    __tablename__ = "subscriptions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Stripe references
    stripe_subscription_id = Column(String(255), nullable=False, unique=True, index=True)
    stripe_customer_id = Column(String(255), nullable=False, index=True)
    
    # Subscription details
    plan = Column(SQLEnum(SubscriptionPlan), nullable=False)
    status = Column(SQLEnum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.ACTIVE)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    canceled_at = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=False)
    
    # Relationship
    user = relationship("User", back_populates="subscription")

