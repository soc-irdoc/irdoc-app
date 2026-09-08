"""Add sharepoint_url to reports.

Revision ID: 016
Revises: 015
Create Date: 2026-06-11
"""
import sqlalchemy as sa

from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("sharepoint_url", sa.String(1024), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "sharepoint_url")
