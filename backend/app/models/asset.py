import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    asset_type: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="suspected")
    criticality: Mapped[str] = mapped_column(String(20), default="medium")
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    added_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", lazy="noload")  # noqa: F821
    timeline_links: Mapped[list["AssetTimelineLink"]] = relationship(
        "AssetTimelineLink", back_populates="asset", cascade="all, delete-orphan", lazy="noload"
    )
    outgoing_links: Mapped[list["AssetLink"]] = relationship(
        "AssetLink",
        foreign_keys="AssetLink.source_id",
        back_populates="source_asset",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    incoming_links: Mapped[list["AssetLink"]] = relationship(
        "AssetLink",
        foreign_keys="AssetLink.target_id",
        back_populates="target_asset",
        cascade="all, delete-orphan",
        lazy="noload",
    )


class AssetTimelineLink(Base):
    __tablename__ = "asset_timeline_links"

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True
    )
    timeline_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("timeline_entries.id", ondelete="CASCADE"), primary_key=True
    )

    asset: Mapped["Asset"] = relationship("Asset", back_populates="timeline_links", lazy="noload")
    timeline_entry: Mapped["TimelineEntry"] = relationship(  # noqa: F821
        "TimelineEntry", back_populates="asset_links", lazy="noload"
    )


class AssetLink(Base):
    __tablename__ = "asset_links"
    __table_args__ = (
        CheckConstraint("source_id != target_id", name="ck_asset_links_no_self_link"),
        UniqueConstraint("source_id", "target_id", "link_type", name="uq_asset_links_triple"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    link_type: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source_asset: Mapped["Asset"] = relationship(
        "Asset", foreign_keys=[source_id], back_populates="outgoing_links", lazy="noload"
    )
    target_asset: Mapped["Asset"] = relationship(
        "Asset", foreign_keys=[target_id], back_populates="incoming_links", lazy="noload"
    )
