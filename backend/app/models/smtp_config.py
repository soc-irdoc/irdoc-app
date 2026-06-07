import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SmtpConfig(Base):
    __tablename__ = "smtp_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, server_default="false")
    host: Mapped[str | None] = mapped_column(Text, nullable=True)
    port: Mapped[int] = mapped_column(Integer, server_default="587")
    use_tls: Mapped[bool] = mapped_column(Boolean, server_default="true")
    username: Mapped[str | None] = mapped_column(Text, nullable=True)
    password_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject_template: Mapped[str] = mapped_column(
        Text, server_default="You've been invited to join {org_name}"
    )
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    accent_color: Mapped[str] = mapped_column(Text, server_default="#6c63ff")
    footer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(  # noqa: F821
        "Organization", lazy="noload"
    )
