import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AiConfig(Base):
    __tablename__ = "ai_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, server_default="false")
    ollama_base_url: Mapped[str] = mapped_column(Text, server_default="http://ollama:11434")
    model_name: Mapped[str] = mapped_column(Text, server_default="llama3.2")
    debounce_seconds: Mapped[int] = mapped_column(Integer, server_default="60")
    max_timeline_events: Mapped[int] = mapped_column(Integer, server_default="20")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(  # noqa: F821
        "Organization", lazy="noload"
    )
