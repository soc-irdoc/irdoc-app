import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(30), default="analyst")
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    avatar_initials: Mapped[str | None] = mapped_column(String(4), nullable=True)
    timezone: Mapped[str] = mapped_column(String(60), default="UTC")
    theme: Mapped[str] = mapped_column(String(20), default="dark")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_reset_password: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, server_default="false", default=False, nullable=False)
    totp_secret: Mapped[str | None] = mapped_column(Text, nullable=True)  # Fernet-encrypted
    backup_codes: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    mfa_enrolled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(20), server_default="local", default="local", nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="users", lazy="noload")  # noqa: F821
