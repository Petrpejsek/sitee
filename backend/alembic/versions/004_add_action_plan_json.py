"""Add action_plan_json column to audit_outputs for Stage B pipeline

Revision ID: 004
Revises: 003
Create Date: 2025-12-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    """Add action_plan_json column to audit_outputs table"""
    op.add_column(
        'audit_outputs',
        sa.Column('action_plan_json', JSONB, nullable=True)
    )


def downgrade():
    """Remove action_plan_json column from audit_outputs table"""
    op.drop_column('audit_outputs', 'action_plan_json')

