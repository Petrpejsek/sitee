"""Add audit_output_snapshots table for historical runs (retention UI)

Revision ID: 005
Revises: 004
Create Date: 2025-12-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    """Create audit_output_snapshots table"""
    op.create_table(
        "audit_output_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("audit_job_id", UUID(as_uuid=True), sa.ForeignKey("audit_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("audit_json", JSONB, nullable=False),
        sa.Column("action_plan_json", JSONB, nullable=True),
        sa.Column("sampled_urls", JSONB, nullable=True),
        sa.Column("model", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("run_id", UUID(as_uuid=True), nullable=False),
    )
    op.create_index(
        "ix_audit_output_snapshots_audit_job_id",
        "audit_output_snapshots",
        ["audit_job_id"],
        unique=False,
    )


def downgrade():
    """Drop audit_output_snapshots table"""
    op.drop_index("ix_audit_output_snapshots_audit_job_id", table_name="audit_output_snapshots")
    op.drop_table("audit_output_snapshots")



