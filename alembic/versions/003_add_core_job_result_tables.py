"""Add core Job and Result tables

Revision ID: 003_add_core_job_result_tables
Revises: 002_add_etl_invoices
Create Date: 2025-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_core_job_result_tables'
down_revision = '002_add_etl_invoices'
branch_labels = None
depends_on = None


def upgrade():
    # Create jobs table
    op.create_table(
        'jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('progress', sa.String(), nullable=True),
        sa.Column('stage', sa.String(), nullable=True),
        sa.Column('source_type', sa.String(), nullable=True),
        sa.Column('filename', sa.String(), nullable=True),
        sa.Column('file_size', sa.String(), nullable=True),
        sa.Column('checksum', sa.String(), nullable=True),
        sa.Column('job_metadata', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('attempts', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_jobs_status', 'jobs', ['status'])
    op.create_index('ix_jobs_created_at', 'jobs', ['created_at'])
    
    # Create results table
    op.create_table(
        'results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('job_id', sa.String(), nullable=False),
        sa.Column('schema_version', sa.String(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('validation', sa.JSON(), nullable=True),
        sa.Column('models_used', sa.JSON(), nullable=True),
        sa.Column('provenance', sa.JSON(), nullable=True),
        sa.Column('raw_ocr_output', sa.JSON(), nullable=True),
        sa.Column('object_storage_key', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_results_job_id', 'results', ['job_id'])
    op.create_index('ix_results_created_at', 'results', ['created_at'])
    
    # Create models table
    op.create_table(
        'models',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('model_type', sa.String(), nullable=False),
        sa.Column('checkpoint_id', sa.String(), nullable=True),
        sa.Column('dataset_ids', sa.JSON(), nullable=True),
        sa.Column('model_metadata', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_models_name_version', 'models', ['name', 'version'])
    
    # Create active_learning table
    op.create_table(
        'active_learning',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('job_id', sa.String(), nullable=False),
        sa.Column('result_id', sa.String(), nullable=True),
        sa.Column('model_version', sa.String(), nullable=True),
        sa.Column('original', sa.JSON(), nullable=False),
        sa.Column('correction', sa.JSON(), nullable=True),
        sa.Column('ocr_payload', sa.JSON(), nullable=True),
        sa.Column('model_output', sa.JSON(), nullable=True),
        sa.Column('needs_review', sa.String(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('exported', sa.String(), nullable=True),
        sa.Column('exported_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['result_id'], ['results.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_active_learning_job_id', 'active_learning', ['job_id'])
    op.create_index('ix_active_learning_exported', 'active_learning', ['exported'])


def downgrade():
    op.drop_index('ix_active_learning_exported', table_name='active_learning')
    op.drop_index('ix_active_learning_job_id', table_name='active_learning')
    op.drop_table('active_learning')
    op.drop_index('ix_models_name_version', table_name='models')
    op.drop_table('models')
    op.drop_index('ix_results_created_at', table_name='results')
    op.drop_index('ix_results_job_id', table_name='results')
    op.drop_table('results')
    op.drop_index('ix_jobs_created_at', table_name='jobs')
    op.drop_index('ix_jobs_status', table_name='jobs')
    op.drop_table('jobs')

