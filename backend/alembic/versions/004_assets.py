"""Phase 4b — assets, asset_timeline_links, asset_links tables

Revision ID: 004
Revises: 003
Create Date: 2026-03-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── assets ────────────────────────────────────────────────────────────────
    op.create_table(
        "assets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("asset_type", sa.String(30), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="suspected"),
        sa.Column("criticality", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("tags", postgresql.ARRAY(sa.Text), nullable=False, server_default="{}"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "added_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_assets_incident_id", "assets", ["incident_id"])
    op.create_index("ix_assets_incident_type", "assets", ["incident_id", "asset_type"])
    op.create_index("ix_assets_status", "assets", ["incident_id", "status"])

    # ── asset_timeline_links ──────────────────────────────────────────────────
    op.create_table(
        "asset_timeline_links",
        sa.Column(
            "asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "timeline_entry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("timeline_entries.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index(
        "ix_asset_timeline_links_entry",
        "asset_timeline_links",
        ["timeline_entry_id"],
    )

    # ── asset_links ───────────────────────────────────────────────────────────
    op.create_table(
        "asset_links",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("link_type", sa.String(40), nullable=False),
        sa.Column("label", sa.Text, nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("source_id != target_id", name="ck_asset_links_no_self_link"),
        sa.UniqueConstraint("source_id", "target_id", "link_type", name="uq_asset_links_triple"),
    )
    op.create_index("ix_asset_links_incident", "asset_links", ["incident_id"])
    op.create_index("ix_asset_links_source", "asset_links", ["source_id"])
    op.create_index("ix_asset_links_target", "asset_links", ["target_id"])


def downgrade() -> None:
    op.drop_table("asset_links")
    op.drop_table("asset_timeline_links")
    op.drop_table("assets")
