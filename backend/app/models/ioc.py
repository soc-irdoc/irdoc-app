import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class IOC(Base):
    __tablename__ = "iocs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    ioc_type: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[int] = mapped_column(Integer, default=50)
    status: Mapped[str] = mapped_column(String(20), default="active")
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    added_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    enrichment: Mapped[dict] = mapped_column(JSONB, default=dict)
    tlp_level: Mapped[str] = mapped_column(String(10), default="red")
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", back_populates="iocs", lazy="noload")  # noqa: F821
    timeline_links: Mapped[list["IOCTimelineLink"]] = relationship(
        "IOCTimelineLink", back_populates="ioc", cascade="all, delete-orphan", lazy="noload"
    )


class IOCTimelineLink(Base):
    __tablename__ = "ioc_timeline_links"

    ioc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("iocs.id", ondelete="CASCADE"), primary_key=True
    )
    timeline_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("timeline_entries.id", ondelete="CASCADE"), primary_key=True
    )

    ioc: Mapped["IOC"] = relationship("IOC", back_populates="timeline_links", lazy="noload")
    timeline_entry: Mapped["TimelineEntry"] = relationship(  # noqa: F821
        "TimelineEntry", back_populates="ioc_links", lazy="noload"
    )
