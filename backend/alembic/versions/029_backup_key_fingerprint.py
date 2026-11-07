"""add backup_records.key_fingerprint (#149)

Revision ID: 029
Revises: 028
Create Date: 2026-11-07
"""
import sqlalchemy as sa

from alembic import op

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NULL = legacy backup encrypted with the SECRET_KEY-derived key.
    op.add_column("backup_records", sa.Column("key_fingerprint", sa.String(16), nullable=True))


def downgrade() -> None:
    op.drop_column("backup_records", "key_fingerprint")
