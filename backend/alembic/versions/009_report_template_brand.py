"""Add brand fields to report_templates.

Revision ID: 009
Revises: 008
Create Date: 2026-05-24
"""
import sqlalchemy as sa

from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("report_templates", sa.Column("logo_data_uri", sa.Text(), nullable=True))
    op.add_column("report_templates", sa.Column("primary_colour", sa.String(7), nullable=True))
    op.add_column("report_templates", sa.Column("company_name", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("report_templates", "company_name")
    op.drop_column("report_templates", "primary_colour")
    op.drop_column("report_templates", "logo_data_uri")
