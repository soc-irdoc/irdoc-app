"""add last_otp_counter to users for TOTP replay protection

Revision ID: 021
Revises: 020
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_otp_counter", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_otp_counter")
