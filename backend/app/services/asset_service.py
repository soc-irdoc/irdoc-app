"""
Asset service: CRUD for assets, asset-timeline links, and asset-to-asset links.
"""
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetLink, AssetTimelineLink
from app.schemas.asset import AssetBulkCreate, AssetCreate, AssetLinkCreate, AssetUpdate


async def create_asset(
    db: AsyncSession,
    incident_id: str,
    data: AssetCreate,
    added_by: str | None = None,
) -> Asset:
    asset = Asset(
        incident_id=incident_id,
        asset_type=data.asset_type,
        name=data.name,
        description=data.description,
        status=data.status,
        criticality=data.criticality,
        tags=data.tags,
        metadata_=data.metadata,
        added_by=added_by,
    )
    db.add(asset)
    await db.flush()
    await db.refresh(asset)
    return asset


async def bulk_create_assets(
    db: AsyncSession,
    incident_id: str,
    data: AssetBulkCreate,
    added_by: str | None = None,
) -> list[Asset]:
    assets = []
    for name in data.names:
        name = name.strip()
        if not name:
            continue
        asset = Asset(
            incident_id=incident_id,
            asset_type=data.asset_type,
            name=name,
            description=data.description,
            status=data.status,
            criticality=data.criticality,
            tags=data.tags,
            metadata_={},
            added_by=added_by,
        )
        db.add(asset)
        assets.append(asset)
    await db.flush()
    for asset in assets:
        await db.refresh(asset)
    return assets


async def list_assets(db: AsyncSession, incident_id: str) -> list[Asset]:
    result = await db.execute(
        select(Asset).where(Asset.incident_id == incident_id).order_by(Asset.created_at)
    )
    return list(result.scalars().all())


async def get_asset(db: AsyncSession, asset_id: str, incident_id: str) -> Asset:
    result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.incident_id == incident_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return asset


async def update_asset(db: AsyncSession, asset: Asset, data: AssetUpdate) -> Asset:
    for key, value in data.model_dump(exclude_none=True).items():
        if key == "metadata":
            asset.metadata_ = value
        else:
            setattr(asset, key, value)
    await db.flush()
    await db.refresh(asset)
    return asset


async def delete_asset(db: AsyncSession, asset: Asset) -> None:
    await db.delete(asset)
    await db.flush()


# ── Timeline links ────────────────────────────────────────────────────────────

async def link_assets_to_entry(
    db: AsyncSession,
    asset_ids: list[uuid.UUID],
    timeline_entry_id: uuid.UUID,
) -> None:
    """Link one or more assets to a timeline entry (idempotent)."""
    # Check existing links to avoid unique violations
    result = await db.execute(
        select(AssetTimelineLink).where(
            AssetTimelineLink.timeline_entry_id == timeline_entry_id
        )
    )
    existing_asset_ids = {row.asset_id for row in result.scalars().all()}

    for asset_id in asset_ids:
        if asset_id not in existing_asset_ids:
            link = AssetTimelineLink(
                asset_id=asset_id,
                timeline_entry_id=timeline_entry_id,
            )
            db.add(link)
    await db.flush()


async def unlink_asset_from_entry(
    db: AsyncSession,
    asset_id: uuid.UUID,
    timeline_entry_id: uuid.UUID,
) -> None:
    result = await db.execute(
        select(AssetTimelineLink).where(
            AssetTimelineLink.asset_id == asset_id,
            AssetTimelineLink.timeline_entry_id == timeline_entry_id,
        )
    )
    link = result.scalar_one_or_none()
    if link:
        await db.delete(link)
        await db.flush()


async def list_entry_assets(
    db: AsyncSession,
    timeline_entry_id: uuid.UUID,
) -> list[Asset]:
    """Return all assets linked to a timeline entry."""
    result = await db.execute(
        select(Asset)
        .join(AssetTimelineLink, AssetTimelineLink.asset_id == Asset.id)
        .where(AssetTimelineLink.timeline_entry_id == timeline_entry_id)
        .order_by(Asset.asset_type, Asset.name)
    )
    return list(result.scalars().all())


# ── Asset-to-asset links ──────────────────────────────────────────────────────

async def create_asset_link(
    db: AsyncSession,
    incident_id: str,
    data: AssetLinkCreate,
    created_by: str | None = None,
) -> AssetLink:
    if str(data.source_id) == str(data.target_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot link an asset to itself",
        )

    # Check for duplicate
    existing = await db.execute(
        select(AssetLink).where(
            AssetLink.source_id == data.source_id,
            AssetLink.target_id == data.target_id,
            AssetLink.link_type == data.link_type,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This asset relationship already exists",
        )

    link = AssetLink(
        incident_id=incident_id,
        source_id=data.source_id,
        target_id=data.target_id,
        link_type=data.link_type,
        label=data.label,
        created_by=created_by,
    )
    db.add(link)
    await db.flush()
    await db.refresh(link)
    return link


async def list_asset_links(db: AsyncSession, incident_id: str) -> list[AssetLink]:
    result = await db.execute(
        select(AssetLink)
        .where(AssetLink.incident_id == incident_id)
        .order_by(AssetLink.created_at)
    )
    return list(result.scalars().all())


async def delete_asset_link(
    db: AsyncSession,
    link_id: str,
    incident_id: str,
) -> None:
    result = await db.execute(
        select(AssetLink).where(
            AssetLink.id == link_id,
            AssetLink.incident_id == incident_id,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset link not found",
        )
    await db.delete(link)
    await db.flush()
