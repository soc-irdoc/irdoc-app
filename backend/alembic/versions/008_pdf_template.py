"""Replace docx_templates with pdf_templates; update reports table.

Revision ID: 008
Revises: 007
Create Date: 2026-05-23
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Create pdf_templates ──────────────────────────────────────────────────
    op.create_table(
        "pdf_templates",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("original_docx_path", sa.String(500), nullable=True),
        sa.Column("prefix_html", sa.Text(), nullable=True),
        sa.Column("suffix_html", sa.Text(), nullable=True),
        sa.Column("page_css", sa.Text(), nullable=True),
        sa.Column("mammoth_warnings", postgresql.JSONB(), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pdf_templates_org_id", "pdf_templates", ["org_id"])

    # ── Update reports ────────────────────────────────────────────────────────
    op.add_column("reports", sa.Column(
        "pdf_template_id",
        postgresql.UUID(as_uuid=False),
        sa.ForeignKey("pdf_templates.id", ondelete="SET NULL"),
        nullable=True,
    ))
    op.drop_column("reports", "format")
    op.execute("UPDATE reports SET report_template_id = NULL")
    op.drop_constraint("reports_report_template_id_fkey", "reports", type_="foreignkey")
    op.drop_column("reports", "report_template_id")

    # ── Drop docx_templates ───────────────────────────────────────────────────
    op.drop_index("ix_docx_templates_org_id", "docx_templates")
    op.drop_table("docx_templates")


def downgrade() -> None:
    op.create_table(
        "docx_templates",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("storage_path", sa.String(500), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_docx_templates_org_id", "docx_templates", ["org_id"])
    op.add_column("reports", sa.Column("format", sa.String(20), nullable=False, server_default="pdf"))
    op.add_column("reports", sa.Column(
        "report_template_id",
        postgresql.UUID(as_uuid=False),
        sa.ForeignKey("report_templates.id"),
        nullable=True,
    ))
    op.drop_column("reports", "pdf_template_id")
    op.drop_index("ix_pdf_templates_org_id", "pdf_templates")
    op.drop_table("pdf_templates")
