"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2025-12-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create audit_jobs table
    op.create_table(
        'audit_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('target_domain', sa.String(length=255), nullable=False),
        sa.Column('competitor_domains', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('locale', sa.String(length=10), nullable=False),
        sa.Column('company_description', sa.Text(), nullable=True),
        sa.Column('products_services', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('current_stage', sa.String(length=50), nullable=True),
        sa.Column('progress_percent', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('audit_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('report_pdf_path', sa.String(length=500), nullable=True),
        sa.Column('report_html_path', sa.String(length=500), nullable=True),
        sa.Column('scraping_started_at', sa.DateTime(), nullable=True),
        sa.Column('scraping_completed_at', sa.DateTime(), nullable=True),
        sa.Column('llm_started_at', sa.DateTime(), nullable=True),
        sa.Column('llm_completed_at', sa.DateTime(), nullable=True),
        sa.Column('report_generated_at', sa.DateTime(), nullable=True),
        sa.Column('total_pages_scraped', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_jobs_status', 'audit_jobs', ['status'])
    op.create_index('idx_audit_jobs_created_at', 'audit_jobs', ['created_at'], postgresql_ops={'created_at': 'DESC'})
    
    # Create scraped_pages table
    op.create_table(
        'scraped_pages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('audit_job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=False),
        sa.Column('is_target', sa.Boolean(), nullable=True),
        sa.Column('html_content', sa.Text(), nullable=True),
        sa.Column('text_content', sa.Text(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('meta_description', sa.Text(), nullable=True),
        sa.Column('scraped_at', sa.DateTime(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('content_type', sa.String(length=100), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('url_hash', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['audit_job_id'], ['audit_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url_hash')
    )
    op.create_index('idx_scraped_pages_job', 'scraped_pages', ['audit_job_id'])
    op.create_index('idx_scraped_pages_domain', 'scraped_pages', ['domain'])


def downgrade() -> None:
    op.drop_index('idx_scraped_pages_domain', table_name='scraped_pages')
    op.drop_index('idx_scraped_pages_job', table_name='scraped_pages')
    op.drop_table('scraped_pages')
    op.drop_index('idx_audit_jobs_created_at', table_name='audit_jobs')
    op.drop_index('idx_audit_jobs_status', table_name='audit_jobs')
    op.drop_table('audit_jobs')


