"""Create ai_configs table.

Revision ID: 013
Revises: 012
Create Date: 2026-06-07
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_configs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ollama_base_url", sa.Text(), nullable=False, server_default="http://ollama:11434"),
        sa.Column("model_name", sa.Text(), nullable=False, server_default="llama3.2"),
        sa.Column("debounce_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("max_timeline_events", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("org_id"),
    )


def downgrade() -> None:
    op.drop_table("ai_configs")
