"""Add paywall system with users, payments, and subscriptions

Revision ID: 006
Revises: 005
Create Date: 2025-12-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def table_exists(table_name):
    """Check if a table exists"""
    conn = op.get_bind()
    result = conn.execute(text(
        f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')"
    ))
    return result.scalar()


def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    conn = op.get_bind()
    result = conn.execute(text(
        f"SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = '{table_name}' AND column_name = '{column_name}')"
    ))
    return result.scalar()


def index_exists(index_name):
    """Check if an index exists"""
    conn = op.get_bind()
    result = conn.execute(text(
        f"SELECT EXISTS (SELECT FROM pg_indexes WHERE indexname = '{index_name}')"
    ))
    return result.scalar()


def enum_exists(enum_name):
    """Check if an enum type exists"""
    conn = op.get_bind()
    result = conn.execute(text(
        f"SELECT EXISTS (SELECT FROM pg_type WHERE typname = '{enum_name}')"
    ))
    return result.scalar()


def upgrade():
    """Add paywall system tables and columns"""
    
    # Create enums if not exist (using UPPERCASE to match existing enum)
    if not enum_exists('auditaccessstate'):
        op.execute("CREATE TYPE auditaccessstate AS ENUM ('PREVIEW', 'LOCKED', 'UNLOCKED')")
    if not enum_exists('paymenttype'):
        op.execute("CREATE TYPE paymenttype AS ENUM ('AUDIT', 'SUBSCRIPTION')")
    if not enum_exists('paymentstatus'):
        op.execute("CREATE TYPE paymentstatus AS ENUM ('PENDING', 'COMPLETED', 'FAILED', 'REFUNDED')")
    if not enum_exists('subscriptionplan'):
        op.execute("CREATE TYPE subscriptionplan AS ENUM ('STARTER', 'GROWTH', 'SCALE')")
    if not enum_exists('subscriptionstatus'):
        op.execute("CREATE TYPE subscriptionstatus AS ENUM ('ACTIVE', 'CANCELED', 'PAST_DUE')")
    
    # Create users table
    if not table_exists('users'):
        op.create_table(
            "users",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False, unique=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("magic_link_token", sa.String(length=255), nullable=True),
            sa.Column("magic_link_expires_at", sa.DateTime(), nullable=True),
        )
    if not index_exists('ix_users_email'):
        op.create_index("ix_users_email", "users", ["email"], unique=True)
    if not index_exists('ix_users_magic_link_token'):
        op.create_index("ix_users_magic_link_token", "users", ["magic_link_token"], unique=False)
    
    # Create payments table
    if not table_exists('payments'):
        op.create_table(
            "payments",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("audit_id", UUID(as_uuid=True), sa.ForeignKey("audit_jobs.id", ondelete="SET NULL"), nullable=True),
            sa.Column("payment_type", sa.Enum("audit", "subscription", name="paymenttype", create_type=False), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="usd"),
            sa.Column("status", sa.Enum("pending", "completed", "failed", "refunded", name="paymentstatus", create_type=False), nullable=False, server_default="pending"),
            sa.Column("stripe_payment_intent_id", sa.String(length=255), nullable=True),
            sa.Column("stripe_checkout_session_id", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )
    if not index_exists('ix_payments_user_id'):
        op.create_index("ix_payments_user_id", "payments", ["user_id"], unique=False)
    if not index_exists('ix_payments_audit_id'):
        op.create_index("ix_payments_audit_id", "payments", ["audit_id"], unique=False)
    if not index_exists('ix_payments_stripe_payment_intent_id'):
        op.create_index("ix_payments_stripe_payment_intent_id", "payments", ["stripe_payment_intent_id"], unique=False)
    if not index_exists('ix_payments_stripe_checkout_session_id'):
        op.create_index("ix_payments_stripe_checkout_session_id", "payments", ["stripe_checkout_session_id"], unique=True)
    
    # Create subscriptions table
    if not table_exists('subscriptions'):
        op.create_table(
            "subscriptions",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("stripe_subscription_id", sa.String(length=255), nullable=False, unique=True),
            sa.Column("stripe_customer_id", sa.String(length=255), nullable=False),
            sa.Column("plan", sa.Enum("starter", "growth", "scale", name="subscriptionplan", create_type=False), nullable=False),
            sa.Column("status", sa.Enum("active", "canceled", "past_due", name="subscriptionstatus", create_type=False), nullable=False, server_default="active"),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("canceled_at", sa.DateTime(), nullable=True),
            sa.Column("current_period_end", sa.DateTime(), nullable=False),
        )
    if not index_exists('ix_subscriptions_user_id'):
        op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=True)
    if not index_exists('ix_subscriptions_stripe_subscription_id'):
        op.create_index("ix_subscriptions_stripe_subscription_id", "subscriptions", ["stripe_subscription_id"], unique=True)
    if not index_exists('ix_subscriptions_stripe_customer_id'):
        op.create_index("ix_subscriptions_stripe_customer_id", "subscriptions", ["stripe_customer_id"], unique=False)
    
    # Add columns to audit_jobs table
    if not column_exists('audit_jobs', 'user_id'):
        op.add_column("audit_jobs", sa.Column("user_id", UUID(as_uuid=True), nullable=True))
        op.execute("ALTER TABLE audit_jobs ADD CONSTRAINT fk_audit_jobs_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL")
    if not column_exists('audit_jobs', 'audit_access_state'):
        op.execute("ALTER TABLE audit_jobs ADD COLUMN audit_access_state auditaccessstate NOT NULL DEFAULT 'PREVIEW'")
    if not index_exists('ix_audit_jobs_user_id'):
        op.create_index("ix_audit_jobs_user_id", "audit_jobs", ["user_id"], unique=False)
    
    # Backfill existing audits to UNLOCKED state (grandfather existing audits)
    op.execute("UPDATE audit_jobs SET audit_access_state = 'UNLOCKED' WHERE audit_access_state = 'PREVIEW'")
    
    # Create analytics_events table for tracking
    if not table_exists('analytics_events'):
        op.create_table(
            "analytics_events",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("event_type", sa.String(length=100), nullable=False),
            sa.Column("user_id", UUID(as_uuid=True), nullable=True),
            sa.Column("audit_id", UUID(as_uuid=True), nullable=True),
            sa.Column("event_data", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    if not index_exists('ix_analytics_events_event_type'):
        op.create_index("ix_analytics_events_event_type", "analytics_events", ["event_type"], unique=False)
    if not index_exists('ix_analytics_events_user_id'):
        op.create_index("ix_analytics_events_user_id", "analytics_events", ["user_id"], unique=False)
    if not index_exists('ix_analytics_events_audit_id'):
        op.create_index("ix_analytics_events_audit_id", "analytics_events", ["audit_id"], unique=False)
    if not index_exists('ix_analytics_events_created_at'):
        op.create_index("ix_analytics_events_created_at", "analytics_events", ["created_at"], unique=False)


def downgrade():
    """Remove paywall system"""
    
    # Drop analytics_events table
    if index_exists('ix_analytics_events_created_at'):
        op.drop_index("ix_analytics_events_created_at", table_name="analytics_events")
    if index_exists('ix_analytics_events_audit_id'):
        op.drop_index("ix_analytics_events_audit_id", table_name="analytics_events")
    if index_exists('ix_analytics_events_user_id'):
        op.drop_index("ix_analytics_events_user_id", table_name="analytics_events")
    if index_exists('ix_analytics_events_event_type'):
        op.drop_index("ix_analytics_events_event_type", table_name="analytics_events")
    if table_exists('analytics_events'):
        op.drop_table("analytics_events")
    
    # Remove columns from audit_jobs
    if index_exists('ix_audit_jobs_user_id'):
        op.drop_index("ix_audit_jobs_user_id", table_name="audit_jobs")
    if column_exists('audit_jobs', 'audit_access_state'):
        op.drop_column("audit_jobs", "audit_access_state")
    if column_exists('audit_jobs', 'user_id'):
        op.drop_column("audit_jobs", "user_id")
    
    # Drop subscriptions table
    if index_exists('ix_subscriptions_stripe_customer_id'):
        op.drop_index("ix_subscriptions_stripe_customer_id", table_name="subscriptions")
    if index_exists('ix_subscriptions_stripe_subscription_id'):
        op.drop_index("ix_subscriptions_stripe_subscription_id", table_name="subscriptions")
    if index_exists('ix_subscriptions_user_id'):
        op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    if table_exists('subscriptions'):
        op.drop_table("subscriptions")
    
    # Drop payments table
    if index_exists('ix_payments_stripe_checkout_session_id'):
        op.drop_index("ix_payments_stripe_checkout_session_id", table_name="payments")
    if index_exists('ix_payments_stripe_payment_intent_id'):
        op.drop_index("ix_payments_stripe_payment_intent_id", table_name="payments")
    if index_exists('ix_payments_audit_id'):
        op.drop_index("ix_payments_audit_id", table_name="payments")
    if index_exists('ix_payments_user_id'):
        op.drop_index("ix_payments_user_id", table_name="payments")
    if table_exists('payments'):
        op.drop_table("payments")
    
    # Drop users table
    if index_exists('ix_users_magic_link_token'):
        op.drop_index("ix_users_magic_link_token", table_name="users")
    if index_exists('ix_users_email'):
        op.drop_index("ix_users_email", table_name="users")
    if table_exists('users'):
        op.drop_table("users")
    
    # Drop enum types
    if enum_exists('subscriptionstatus'):
        op.execute("DROP TYPE subscriptionstatus")
    if enum_exists('subscriptionplan'):
        op.execute("DROP TYPE subscriptionplan")
    if enum_exists('paymentstatus'):
        op.execute("DROP TYPE paymentstatus")
    if enum_exists('paymenttype'):
        op.execute("DROP TYPE paymenttype")
    if enum_exists('auditaccessstate'):
        op.execute("DROP TYPE auditaccessstate")
