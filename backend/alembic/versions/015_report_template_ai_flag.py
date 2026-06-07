"""Add ai_auto_generate to report_templates.

Revision ID: 015
Revises: 014
Create Date: 2026-06-07
"""
import sqlalchemy as sa
from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "report_templates",
        sa.Column("ai_auto_generate", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("report_templates", "ai_auto_generate")
