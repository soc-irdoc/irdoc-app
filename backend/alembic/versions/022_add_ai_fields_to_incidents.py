"""add ai_summary and ai_recommendations to incidents

Revision ID: 022
Revises: 021
Create Date: 2026-06-28
"""
from alembic import op
import sqlalchemy as sa

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("incidents", sa.Column("ai_summary", sa.Text(), nullable=True))
    op.add_column("incidents", sa.Column("ai_recommendations", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("incidents", "ai_recommendations")
    op.drop_column("incidents", "ai_summary")
