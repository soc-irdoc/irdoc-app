"""add incidents.disposition (#124)

Revision ID: 026
Revises: 025
Create Date: 2026-10-27
"""
import sqlalchemy as sa

from alembic import op

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NULL = not set; incidents closed before this release have none.
    op.add_column("incidents", sa.Column("disposition", sa.String(40), nullable=True))


def downgrade() -> None:
    op.drop_column("incidents", "disposition")
