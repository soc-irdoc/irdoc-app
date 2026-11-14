"""add timeline_entries.time_spent_minutes (#165)

Revision ID: 032
Revises: 031
Create Date: 2026-11-14

Optional effort per timeline entry, in minutes (0 to 24 hours). NULL means
"not tracked", which reports keep apart from 0. Existing entries stay NULL.
"""
import sqlalchemy as sa

from alembic import op

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("timeline_entries", sa.Column("time_spent_minutes", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_timeline_entries_time_spent_range",
        "timeline_entries",
        "time_spent_minutes IS NULL OR (time_spent_minutes >= 0 AND time_spent_minutes <= 1440)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_timeline_entries_time_spent_range", "timeline_entries", type_="check")
    op.drop_column("timeline_entries", "time_spent_minutes")
