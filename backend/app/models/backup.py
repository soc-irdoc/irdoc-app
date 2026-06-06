import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BackupConfig(Base):
    """System-level backup configuration. Managed as a singleton — always get-or-create via the service layer."""

    __tablename__ = "backup_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enabled: Mapped[bool] = mapped_column(Boolean, server_default="false")
    schedule: Mapped[str] = mapped_column(String(20))  # "6h" | "daily" | "weekly" | "monthly"
    retention_days: Mapped[int] = mapped_column(default=90)
    destination: Mapped[str] = mapped_column(String(20), default="local")  # "local" | "cloud"
    last_backup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_backup_status: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "success" | "failed" | "running"
    last_backup_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_backup_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BackupRecord(Base):
    __tablename__ = "backup_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    destination: Mapped[str] = mapped_column(String(20), nullable=False)  # "local" | "cloud"
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # "success" | "failed"
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
