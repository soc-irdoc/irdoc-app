"""Add version_number and ai_raw_content to reports.

Revision ID: 014
Revises: 013
Create Date: 2026-06-07
"""
import sqlalchemy as sa

from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("reports", sa.Column("ai_raw_content", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "ai_raw_content")
    op.drop_column("reports", "version_number")
