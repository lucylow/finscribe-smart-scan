"""Add ETL invoices and line_items tables

Revision ID: 002_etl_invoices
Revises: 001_add_saas_models
Create Date: 2025-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_etl_invoices'
down_revision = '001_add_saas_models'
branch_labels = None
depends_on = None


def upgrade():
    # Create invoices table
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('invoice_number', sa.Text(), nullable=True),
        sa.Column('vendor', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('financial_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('raw_ocr', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('source_path', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create line_items table
    op.create_table(
        'line_items',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('invoice_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('qty', sa.Numeric(), nullable=True),
        sa.Column('unit_price', sa.Numeric(), nullable=True),
        sa.Column('line_total', sa.Numeric(), nullable=True),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on invoice_number for faster lookups
    op.create_index('ix_invoices_invoice_number', 'invoices', ['invoice_number'])
    op.create_index('ix_line_items_invoice_id', 'line_items', ['invoice_id'])


def downgrade():
    op.drop_index('ix_line_items_invoice_id', table_name='line_items')
    op.drop_index('ix_invoices_invoice_number', table_name='invoices')
    op.drop_table('line_items')
    op.drop_table('invoices')

