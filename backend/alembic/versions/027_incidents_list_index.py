"""index incidents by (org_id, created_at) for the paginated list (#127)

The list's default order is newest first within an org.

Revision ID: 027
Revises: 026
Create Date: 2026-10-27
"""
from alembic import op

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_incidents_org_created ON incidents (org_id, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_incidents_org_created")
