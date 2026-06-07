"""Create smtp_configs table.

Revision ID: 012
Revises: 011
Create Date: 2026-06-06
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "smtp_configs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("host", sa.Text(), nullable=True),
        sa.Column("port", sa.Integer(), nullable=False, server_default="587"),
        sa.Column("use_tls", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("username", sa.Text(), nullable=True),
        sa.Column("password_encrypted", sa.Text(), nullable=True),
        sa.Column("from_name", sa.Text(), nullable=True),
        sa.Column("from_address", sa.Text(), nullable=True),
        sa.Column("subject_template", sa.Text(), nullable=False, server_default="You've been invited to join {org_name}"),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("accent_color", sa.Text(), nullable=False, server_default="#6c63ff"),
        sa.Column("footer_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("org_id"),
    )


def downgrade() -> None:
    op.drop_table("smtp_configs")
