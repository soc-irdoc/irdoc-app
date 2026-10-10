"""remove duplicate system templates and prevent them from coming back

Revision ID: 023
Revises: 022
Create Date: 2026-10-09

The backend, worker and beat containers all run seed.py at the same moment on
a fresh install. Before seed.py took an advisory lock, two of them could both
see empty template tables and each insert the full set, leaving every system
incident template and system report template in the database twice (#93).

This keeps the oldest copy of each system template, points every reference
(incidents, tasks, reports, sync policies) at it, deletes the extra copies,
and adds partial unique indexes so a duplicate system template can never be
inserted again. A system template stays visible if any of its copies was
visible, so an admin who hid one copy as a workaround does not lose it.

Org-owned (custom) templates are never touched.
"""
from alembic import op

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def _dedupe(table: str, key: str, references: list[tuple[str, str]]) -> None:
    # dupes maps every extra copy to the copy being kept for its key.
    dupes_cte = f"""
        WITH ranked AS (
            SELECT id, {key},
                   row_number() OVER (PARTITION BY {key} ORDER BY created_at, id) AS rn,
                   first_value(id) OVER (PARTITION BY {key} ORDER BY created_at, id) AS keep_id
            FROM {table}
            WHERE is_system AND org_id IS NULL
        ),
        dupes AS (SELECT id AS dupe_id, keep_id FROM ranked WHERE rn > 1)
    """

    op.execute(f"""
        UPDATE {table} AS t
        SET is_hidden = g.all_hidden
        FROM (
            SELECT {key}, bool_and(is_hidden) AS all_hidden,
                   (array_agg(id ORDER BY created_at, id))[1] AS keep_id
            FROM {table}
            WHERE is_system AND org_id IS NULL
            GROUP BY {key}
            HAVING count(*) > 1
        ) AS g
        WHERE t.id = g.keep_id
    """)

    for ref_table, ref_column in references:
        op.execute(f"""
            {dupes_cte}
            UPDATE {ref_table} AS r
            SET {ref_column} = d.keep_id
            FROM dupes AS d
            WHERE r.{ref_column} = d.dupe_id
        """)

    op.execute(f"""
        {dupes_cte}
        DELETE FROM {table} WHERE id IN (SELECT dupe_id FROM dupes)
    """)

    op.execute(f"""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_{table}_system_{key}
        ON {table} ({key})
        WHERE is_system AND org_id IS NULL
    """)


def upgrade() -> None:
    _dedupe(
        "incident_templates",
        "slug",
        [("incidents", "template_id"), ("tasks", "template_id")],
    )
    _dedupe(
        "report_templates",
        "name",
        [("reports", "report_template_id"), ("sync_policies", "report_template_id")],
    )


def downgrade() -> None:
    # Deleted duplicates are not restored - they were identical copies.
    op.execute("DROP INDEX IF EXISTS uq_report_templates_system_name")
    op.execute("DROP INDEX IF EXISTS uq_incident_templates_system_slug")
