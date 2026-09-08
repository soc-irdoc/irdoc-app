"""Initial schema — all Phase 1 tables

Revision ID: 001
Revises:
Create Date: 2026-03-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── organizations ──────────────────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("plan", sa.String(20), server_default="core"),
        sa.Column("license_key", sa.Text, nullable=True),
        sa.Column("settings", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("email", sa.Text, unique=True, nullable=False),
        sa.Column("full_name", sa.Text, nullable=False),
        sa.Column("role", sa.String(30), server_default="analyst"),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("avatar_initials", sa.String(4), nullable=True),
        sa.Column("timezone", sa.String(60), server_default="UTC"),
        sa.Column("theme", sa.String(20), server_default="dark"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("must_reset_password", sa.Boolean, server_default="false"),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── api_keys ───────────────────────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("key_prefix", sa.String(20), nullable=False),
        sa.Column("key_hash", sa.Text, nullable=False),
        sa.Column("scopes", postgresql.ARRAY(sa.Text), server_default="{}"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── incident_templates ────────────────────────────────────────────────────
    op.create_table(
        "incident_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_system", sa.Boolean, server_default="false"),
        sa.Column("tasks_json", postgresql.JSONB, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── incidents ──────────────────────────────────────────────────────────────
    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("incident_ref", sa.String(30), unique=True, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("severity", sa.String(10), server_default="sev1"),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incident_templates.id"), nullable=True),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("contained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executive_summary", sa.Text, nullable=True),
        sa.Column("attack_vector", postgresql.ARRAY(sa.Text), server_default="{}"),
        sa.Column("affected_users", sa.Integer, server_default="0"),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── incident_external_refs ─────────────────────────────────────────────────
    op.create_table(
        "incident_external_refs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_source", sa.Text, nullable=False),
        sa.Column("external_ref", sa.Text, nullable=False),
        sa.Column("external_url", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("incident_id", "external_source"),
    )

    # ── timeline_entries ───────────────────────────────────────────────────────
    op.create_table(
        "timeline_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("entry_type", sa.String(30), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("source", sa.String(50), server_default="manual"),
        sa.Column("is_pinned", sa.Boolean, server_default="false"),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── attachments ────────────────────────────────────────────────────────────
    op.create_table(
        "attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timeline_entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("timeline_entries.id", ondelete="CASCADE"), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("original_name", sa.Text, nullable=False),
        sa.Column("stored_path", sa.Text, nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("file_size", sa.BigInteger, nullable=True),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_backend", sa.String(20), server_default="local"),
        sa.Column("is_screenshot", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── iocs ───────────────────────────────────────────────────────────────────
    op.create_table(
        "iocs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ioc_type", sa.String(20), nullable=False),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("confidence", sa.Integer, server_default="50"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("first_seen", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("added_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("enrichment", postgresql.JSONB, server_default="{}"),
        sa.Column("tlp_level", sa.String(10), server_default="red"),
        sa.Column("tags", postgresql.ARRAY(sa.Text), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── ioc_timeline_links ─────────────────────────────────────────────────────
    op.create_table(
        "ioc_timeline_links",
        sa.Column("ioc_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("iocs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("timeline_entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("timeline_entries.id", ondelete="CASCADE"), primary_key=True),
    )

    # ── tasks ──────────────────────────────────────────────────────────────────
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incident_templates.id"), nullable=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("phase", sa.String(50), nullable=True),
        sa.Column("priority", sa.String(20), server_default="medium"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("sort_order", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── report_templates ───────────────────────────────────────────────────────
    op.create_table(
        "report_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("destination", sa.String(30), server_default="custom"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_system", sa.Boolean, server_default="false"),
        sa.Column("is_default", sa.Boolean, server_default="false"),
        sa.Column("schema_json", postgresql.JSONB, server_default="[]"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── reports ────────────────────────────────────────────────────────────────
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("report_template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("report_templates.id"), nullable=True),
        sa.Column("report_type", sa.String(30), nullable=False),
        sa.Column("destination", sa.String(30), nullable=True),
        sa.Column("format", sa.String(20), nullable=False),
        sa.Column("classification", sa.String(30), server_default="confidential"),
        sa.Column("generated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("storage_path", sa.Text, nullable=True),
        sa.Column("is_ai_assisted", sa.Boolean, server_default="false"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── sync_policies ──────────────────────────────────────────────────────────
    op.create_table(
        "sync_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("destination", sa.Text, nullable=False),
        sa.Column("report_template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("report_templates.id"), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("trigger_type", sa.String(20), server_default="on_change"),
        sa.Column("debounce_seconds", sa.Integer, server_default="60"),
        sa.Column("destination_config", postgresql.JSONB, server_default="{}"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(20), nullable=True),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── storage_configs ────────────────────────────────────────────────────────
    op.create_table(
        "storage_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), unique=True, nullable=False),
        sa.Column("backend", sa.String(20), server_default="local"),
        sa.Column("config", postgresql.JSONB, server_default="{}"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("last_tested", sa.DateTime(timezone=True), nullable=True),
        sa.Column("test_status", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── audit_log ──────────────────────────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("api_keys.id"), nullable=True),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("entity_type", sa.Text, nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("diff", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", postgresql.INET, nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── Indexes ────────────────────────────────────────────────────────────────
    op.create_index("idx_timeline_incident_time", "timeline_entries", ["incident_id", sa.text("occurred_at DESC")])
    op.create_index("idx_timeline_fts", "timeline_entries", [sa.text("to_tsvector('english', description)")], postgresql_using="gin")
    op.create_index("idx_ioc_incident", "iocs", ["incident_id", "ioc_type"])
    op.create_index("idx_ioc_value", "iocs", ["value"])
    op.create_index("idx_tasks_incident", "tasks", ["incident_id", "status"])
    op.create_index("idx_attachments_entry", "attachments", ["timeline_entry_id"])
    op.create_index("idx_incidents_ref", "incidents", ["incident_ref"])
    op.create_index("idx_incidents_org_status", "incidents", ["org_id", "status", "severity"])
    op.create_index("idx_external_refs_incident", "incident_external_refs", ["incident_id"])
    op.create_index("idx_external_refs_source", "incident_external_refs", ["external_source", "external_ref"])
    op.create_index("idx_audit_org_time", "audit_log", ["org_id", sa.text("created_at DESC")])
    op.create_index("idx_api_keys_org", "api_keys", ["org_id", "is_active"])


def downgrade() -> None:
    # Drop in reverse dependency order
    for table in [
        "audit_log", "storage_configs", "sync_policies", "reports",
        "report_templates", "tasks", "ioc_timeline_links", "iocs",
        "attachments", "timeline_entries", "incident_external_refs",
        "incidents", "incident_templates", "api_keys", "users", "organizations",
    ]:
        op.drop_table(table)
