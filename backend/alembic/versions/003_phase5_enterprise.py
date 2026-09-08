"""Phase 5 — user_invites table + sso_configs table + RLS policies

Revision ID: 003
Revises: 002
Create Date: 2026-03-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── user_invites ──────────────────────────────────────────────────────────
    op.create_table(
        "user_invites",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invited_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("token", sa.Text, unique=True, nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    op.create_index("ix_user_invites_token", "user_invites", ["token"], unique=True)
    op.create_index(
        "ix_user_invites_org_email", "user_invites", ["org_id", "email"]
    )

    # ── sso_configs ───────────────────────────────────────────────────────────
    op.create_table(
        "sso_configs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("provider", sa.Text, nullable=False, server_default="saml"),
        sa.Column("idp_metadata_url", sa.Text, nullable=True),
        sa.Column("entity_id", sa.Text, nullable=True),
        sa.Column("sso_url", sa.Text, nullable=True),
        sa.Column("certificate", sa.Text, nullable=True),
        sa.Column("attr_email", sa.Text, nullable=True),
        sa.Column("attr_name", sa.Text, nullable=True),
        sa.Column("attr_groups", sa.Text, nullable=True),
        sa.Column(
            "role_mappings",
            postgresql.JSONB,
            server_default="{}",
            nullable=False,
        ),
        sa.Column("is_enabled", sa.Boolean, server_default="false", nullable=False),
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

    # ── Row-Level Security policies ───────────────────────────────────────────
    op.execute("ALTER TABLE incidents ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE timeline_entries ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE iocs ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE attachments ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE reports ENABLE ROW LEVEL SECURITY;")

    op.execute(
        "CREATE POLICY org_isolation_incidents ON incidents "
        "USING (org_id = current_setting('app.current_org_id', true)::uuid);"
    )
    op.execute(
        "CREATE POLICY org_isolation_timeline ON timeline_entries "
        "USING (incident_id IN (SELECT id FROM incidents WHERE org_id = current_setting('app.current_org_id', true)::uuid));"
    )
    op.execute(
        "CREATE POLICY org_isolation_iocs ON iocs "
        "USING (incident_id IN (SELECT id FROM incidents WHERE org_id = current_setting('app.current_org_id', true)::uuid));"
    )
    op.execute(
        "CREATE POLICY org_isolation_attachments ON attachments "
        "USING (org_id = current_setting('app.current_org_id', true)::uuid);"
    )
    op.execute(
        "CREATE POLICY org_isolation_tasks ON tasks "
        "USING (incident_id IN (SELECT id FROM incidents WHERE org_id = current_setting('app.current_org_id', true)::uuid));"
    )
    op.execute(
        "CREATE POLICY org_isolation_reports ON reports "
        "USING (incident_id IN (SELECT id FROM incidents WHERE org_id = current_setting('app.current_org_id', true)::uuid));"
    )


def downgrade() -> None:
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS org_isolation_incidents ON incidents;")
    op.execute("DROP POLICY IF EXISTS org_isolation_timeline ON timeline_entries;")
    op.execute("DROP POLICY IF EXISTS org_isolation_iocs ON iocs;")
    op.execute("DROP POLICY IF EXISTS org_isolation_attachments ON attachments;")
    op.execute("DROP POLICY IF EXISTS org_isolation_tasks ON tasks;")
    op.execute("DROP POLICY IF EXISTS org_isolation_reports ON reports;")

    op.execute("ALTER TABLE incidents DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE timeline_entries DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE iocs DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE attachments DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tasks DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE reports DISABLE ROW LEVEL SECURITY;")

    op.drop_index("ix_user_invites_org_email", table_name="user_invites")
    op.drop_index("ix_user_invites_token", table_name="user_invites")
    op.drop_table("sso_configs")
    op.drop_table("user_invites")
