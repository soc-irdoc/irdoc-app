"""make incident template slugs unique per org (#168)

Revision ID: 031
Revises: 030
Create Date: 2026-11-14

The inbound webhook picks a template by slug. Org templates could share a
slug, which made that lookup fail with a 500. This renames the extra copies
in each (org_id, slug) group and adds a partial unique index so it can't
happen again.

Per group, the oldest template keeps its slug and the others get
"-<first 8 characters of their id>" appended (trimmed to fit 100 characters).
No row is deleted and nothing that references a template changes: incidents
point at template ids, not slugs.

An org template that shares a slug with a system template is left as it is.
The webhook prefers the org's own template, and the API refuses new
collisions (template_service._ensure_slug_available).
"""
from alembic import op

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (PARTITION BY org_id, slug ORDER BY created_at, id) AS rn
            FROM incident_templates
            WHERE org_id IS NOT NULL
        )
        UPDATE incident_templates t
        SET slug = left(t.slug, 91) || '-' || left(t.id::text, 8)
        FROM ranked r
        WHERE t.id = r.id AND r.rn > 1
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_incident_templates_org_slug
        ON incident_templates (org_id, slug)
        WHERE org_id IS NOT NULL
        """
    )


def downgrade() -> None:
    # Renamed slugs are not restored: the old values were duplicates.
    op.execute("DROP INDEX IF EXISTS uq_incident_templates_org_slug")
