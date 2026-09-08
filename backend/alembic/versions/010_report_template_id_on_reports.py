"""Add report_template_id FK to reports.

Revision ID: 010
Revises: 009
Create Date: 2026-05-24
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reports", sa.Column(
        "report_template_id",
        postgresql.UUID(as_uuid=False),
        sa.ForeignKey("report_templates.id", ondelete="SET NULL"),
        nullable=True,
    ))


def downgrade() -> None:
    op.drop_constraint("reports_report_template_id_fkey", "reports", type_="foreignkey")
    op.drop_column("reports", "report_template_id")
