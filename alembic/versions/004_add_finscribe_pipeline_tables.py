"""Add finscribe pipeline tables (OCRResult, ParsedResult)

Revision ID: 004_add_finscribe_pipeline_tables
Revises: 003_add_core_job_result_tables
Create Date: 2025-01-21 12:00:00.000000

Note: The 'jobs' table already exists from migration 003, so we only create
ocr_results and parsed_results tables here. These tables use job_id as a 
reference to the existing jobs table.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_add_finscribe_pipeline_tables'
down_revision = '003_add_core_job_result_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create OCR results table
    op.create_table(
        "ocr_results",
        sa.Column("job_id", sa.String(), primary_key=True),
        sa.Column("data", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
    )
    
    # Create parsed results table
    op.create_table(
        "parsed_results",
        sa.Column("job_id", sa.String(), primary_key=True),
        sa.Column("structured", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
    )


def downgrade():
    op.drop_table("parsed_results")
    op.drop_table("ocr_results")

