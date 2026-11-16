"""add sso_configs.graph_group_lookup (#172)

Revision ID: 033
Revises: 032
Create Date: 2026-11-16

Opt-in Microsoft Graph lookup of the signing-in user's group membership, for
tokens that don't carry the mapped group Object IDs (on-prem synced groups
emitted as sAMAccountName/SID, group overage, assigned-groups-only claims).
Off for existing configs: turning it on adds the User.Read Graph scope.
"""
import sqlalchemy as sa

from alembic import op

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sso_configs",
        sa.Column("graph_group_lookup", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("sso_configs", "graph_group_lookup")
