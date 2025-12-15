"""Add audit_outputs table

Revision ID: 002
Revises: 001
Create Date: 2025-12-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create audit_outputs table
    op.create_table(
        'audit_outputs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('audit_job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('audit_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('report_html', sa.Text(), nullable=True),
        sa.Column('pdf_path', sa.String(length=500), nullable=True),
        sa.Column('pdf_blob', sa.Text(), nullable=True),
        sa.Column('model', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sampled_urls', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['audit_job_id'], ['audit_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('audit_job_id')
    )
    op.create_index('idx_audit_outputs_job', 'audit_outputs', ['audit_job_id'])
    op.create_index('idx_audit_outputs_created', 'audit_outputs', ['created_at'], postgresql_ops={'created_at': 'DESC'})


def downgrade() -> None:
    op.drop_index('idx_audit_outputs_created', table_name='audit_outputs')
    op.drop_index('idx_audit_outputs_job', table_name='audit_outputs')
    op.drop_table('audit_outputs')


