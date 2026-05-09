import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    incident_ref: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(10), default="sev1")
    status: Mapped[str] = mapped_column(String(20), default="open")
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incident_templates.id"), nullable=True
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    contained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    attack_vector: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    affected_users: Mapped[int] = mapped_column(Integer, default=0)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="incidents", lazy="noload")  # noqa: F821
    assigned_user: Mapped["User | None"] = relationship(  # noqa: F821
        "User", foreign_keys=[assigned_to], lazy="noload"
    )
    external_refs: Mapped[list["IncidentExternalRef"]] = relationship(
        "IncidentExternalRef", back_populates="incident", cascade="all, delete-orphan", lazy="noload"
    )
    timeline_entries: Mapped[list["TimelineEntry"]] = relationship(  # noqa: F821
        "TimelineEntry", back_populates="incident", cascade="all, delete-orphan", lazy="noload"
    )
    iocs: Mapped[list["IOC"]] = relationship(  # noqa: F821
        "IOC", back_populates="incident", cascade="all, delete-orphan", lazy="noload"
    )
    tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        "Task", back_populates="incident", cascade="all, delete-orphan", lazy="noload"
    )


class IncidentExternalRef(Base):
    __tablename__ = "incident_external_refs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    external_source: Mapped[str] = mapped_column(Text, nullable=False)
    external_ref: Mapped[str] = mapped_column(Text, nullable=False)
    external_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    incident: Mapped["Incident"] = relationship("Incident", back_populates="external_refs", lazy="noload")

    __table_args__ = (
        __import__("sqlalchemy").UniqueConstraint("incident_id", "external_source"),
    )
