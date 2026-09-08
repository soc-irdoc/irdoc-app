"""Add notes, lessons_learned, actions_todo to incidents.

Revision ID: 007
Revises: 006
Create Date: 2026-05-23
"""
import sqlalchemy as sa

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("incidents", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("incidents", sa.Column("lessons_learned", sa.Text(), nullable=True))
    op.add_column("incidents", sa.Column("actions_todo", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("incidents", "actions_todo")
    op.drop_column("incidents", "lessons_learned")
    op.drop_column("incidents", "notes")
