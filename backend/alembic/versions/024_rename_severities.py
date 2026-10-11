"""rename incident severities from sev1-sev4 to critical/high/medium/low

Revision ID: 024
Revises: 023
Create Date: 2026-10-11

SEV-1..SEV-4 become Critical, High, Medium and Low (#109). Existing incidents
are converted in place and the column default follows. Audit log entries keep
the values they were written with, since they record what happened at the time.
"""
from alembic import op

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None

_RENAMES = [("sev1", "critical"), ("sev2", "high"), ("sev3", "medium"), ("sev4", "low")]


def _rename(pairs: list[tuple[str, str]], default: str) -> None:
    cases = " ".join(f"WHEN '{old}' THEN '{new}'" for old, new in pairs)
    olds = ", ".join(f"'{old}'" for old, _ in pairs)
    op.execute(
        f"UPDATE incidents SET severity = CASE severity {cases} END WHERE severity IN ({olds})"
    )
    op.alter_column("incidents", "severity", server_default=default)


def upgrade() -> None:
    _rename(_RENAMES, "critical")


def downgrade() -> None:
    _rename([(new, old) for old, new in _RENAMES], "sev1")
