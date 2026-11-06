import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BackupConfig(Base):
    """System-level backup configuration. Managed as a singleton - always get-or-create via the service layer."""

    __tablename__ = "backup_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enabled: Mapped[bool] = mapped_column(Boolean, server_default="false")
    schedule: Mapped[str] = mapped_column(String(20))  # "6h" | "daily" | "weekly" | "monthly"
    retention_days: Mapped[int] = mapped_column(default=90)
    destination: Mapped[str] = mapped_column(String(20), default="local")  # "local" | "cloud" | "sftp" | "smb"
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
    destination: Mapped[str] = mapped_column(String(20), nullable=False)  # "local" | "cloud" | "sftp" | "smb"
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # "success" | "failed"
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Fingerprint of the key the file is encrypted with (#149). NULL = made
    # before 0.1.10 with the SECRET_KEY-derived key (legacy, headerless file).
    key_fingerprint: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BackupRemoteConfig(Base):
    """SFTP / SMB backup destination settings (#151), one row per kind.

    Kept separately from Admin > Storage so backups can live somewhere fully
    independent of the evidence store. ``config`` holds the connection
    settings with every secret Fernet-encrypted (integration_service.encrypt_config).
    """

    __tablename__ = "backup_remote_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # "sftp" | "smb"
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # SFTP only: the pinned server host key (OpenSSH public key line) and its
    # SHA256 fingerprint. Uploads refuse any other key.
    host_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    host_key_fingerprint: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_tested: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    test_status: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "ok" | "failed"
    test_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
