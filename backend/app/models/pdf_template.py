"""PdfTemplate model — company-branded DOCX templates for PDF report generation."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PdfTemplate(Base):
    __tablename__ = "pdf_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    original_docx_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    prefix_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    suffix_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_css: Mapped[str | None] = mapped_column(Text, nullable=True)
    mammoth_warnings: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
