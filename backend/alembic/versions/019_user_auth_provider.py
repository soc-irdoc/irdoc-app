"""Add auth_provider column to users table.

Revision ID: 019
Revises: 018
Create Date: 2026-06-12
"""
import sqlalchemy as sa
from alembic import op

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("auth_provider", sa.String(20), nullable=False, server_default="local"),
    )


def downgrade():
    op.drop_column("users", "auth_provider")
