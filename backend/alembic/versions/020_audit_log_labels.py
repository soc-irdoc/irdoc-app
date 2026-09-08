"""audit_log actor and entity label columns

Revision ID: 020
Revises: 019
Create Date: 2026-06-14
"""
import sqlalchemy as sa

from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_log", sa.Column("actor_label", sa.Text(), nullable=True))
    op.add_column("audit_log", sa.Column("entity_label", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("audit_log", "actor_label")
    op.drop_column("audit_log", "entity_label")
