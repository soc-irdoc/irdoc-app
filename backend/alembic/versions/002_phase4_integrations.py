"""Phase 4 — org_integrations + graph_edges tables

Revision ID: 002
Revises: 001
Create Date: 2026-03-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── org_integrations ──────────────────────────────────────────────────────
    op.create_table(
        "org_integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plugin_name", sa.Text, nullable=False),
        sa.Column("is_enabled", sa.Boolean, server_default="false"),
        sa.Column("config", postgresql.JSONB, server_default="{}"),  # Fernet-encrypted values
        sa.Column("last_tested", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_status", sa.String(10), nullable=True),  # ok | fail
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("org_id", "plugin_name"),
    )

    # ── graph_edges ───────────────────────────────────────────────────────────
    # Stores manually created edges between graph nodes.
    # Auto-edges (IOC→timeline entry, enrichment-derived) are computed at query time.
    op.create_table(
        "graph_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_node_id", sa.Text, nullable=False),  # e.g. "ioc-{uuid}"
        sa.Column("target_node_id", sa.Text, nullable=False),  # e.g. "entry-{uuid}"
        sa.Column("label", sa.Text, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_index("idx_org_integrations_org", "org_integrations", ["org_id", "plugin_name"])
    op.create_index("idx_graph_edges_incident", "graph_edges", ["incident_id"])


def downgrade() -> None:
    op.drop_table("graph_edges")
    op.drop_table("org_integrations")
