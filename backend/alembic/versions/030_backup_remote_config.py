"""add backup_remote_configs for SFTP / SMB destinations (#151)

Revision ID: 030
Revises: 029
Create Date: 2026-11-07
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backup_remote_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(20), nullable=False, unique=True),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("host_key", sa.Text(), nullable=True),
        sa.Column("host_key_fingerprint", sa.String(100), nullable=True),
        sa.Column("last_tested", sa.DateTime(timezone=True), nullable=True),
        sa.Column("test_status", sa.String(20), nullable=True),
        sa.Column("test_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("backup_remote_configs")
