"""add is_hidden to incident_templates and report_templates

Revision ID: 017
Revises: 016
Create Date: 2026-06-11
"""
import sqlalchemy as sa

from alembic import op

revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('incident_templates', sa.Column('is_hidden', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('report_templates', sa.Column('is_hidden', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('incident_templates', 'is_hidden')
    op.drop_column('report_templates', 'is_hidden')
