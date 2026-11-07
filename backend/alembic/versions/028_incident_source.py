"""add incidents.source (#147)

Revision ID: 028
Revises: 027
Create Date: 2026-11-06
"""
import sqlalchemy as sa

from alembic import op

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NULL = not recorded. Existing incidents are deliberately not backfilled:
    # a guessed value would be indistinguishable from a real one in reporting.
    op.add_column("incidents", sa.Column("source", sa.String(40), nullable=True))


def downgrade() -> None:
    op.drop_column("incidents", "source")
