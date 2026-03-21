from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.schemas.asset import (
    AssetBulkCreate,
    AssetCreate,
    AssetLinkCreate,
    AssetLinkOut,
    AssetOut,
    AssetTimelineLinkCreate,
    AssetUpdate,
)
from app.services import asset_service, incident_service

router = APIRouter(tags=["assets"])


# ── Asset CRUD ────────────────────────────────────────────────────────────────

@router.get("/incidents/{incident_id}/assets")
async def list_assets(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("assets.read")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    assets = await asset_service.list_assets(db, incident_id)
    return {"data": [AssetOut.model_validate(a) for a in assets], "error": None}


@router.post("/incidents/{incident_id}/assets", status_code=201)
async def create_asset(
    incident_id: str,
    data: AssetCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("assets.create")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    asset = await asset_service.create_asset(db, incident_id, data, str(current_user.id))
    return {"data": AssetOut.model_validate(asset), "error": None}


@router.post("/incidents/{incident_id}/assets/bulk", status_code=201)
async def bulk_create_assets(
    incident_id: str,
    data: AssetBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("assets.create")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    assets = await asset_service.bulk_create_assets(db, incident_id, data, str(current_user.id))
    return {"data": [AssetOut.model_validate(a) for a in assets], "error": None}


@router.put("/incidents/{incident_id}/assets/{asset_id}")
async def update_asset(
    incident_id: str,
    asset_id: str,
    data: AssetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("assets.update")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    asset = await asset_service.get_asset(db, asset_id, incident_id)
    updated = await asset_service.update_asset(db, asset, data)
    return {"data": AssetOut.model_validate(updated), "error": None}


@router.delete("/incidents/{incident_id}/assets/{asset_id}", status_code=204)
async def delete_asset(
    incident_id: str,
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("assets.delete")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    asset = await asset_service.get_asset(db, asset_id, incident_id)
    await asset_service.delete_asset(db, asset)


# ── Asset-timeline links ──────────────────────────────────────────────────────

@router.post("/incidents/{incident_id}/assets/timeline-links", status_code=201)
async def link_assets_to_entry(
    incident_id: str,
    data: AssetTimelineLinkCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("assets.create")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    await asset_service.link_assets_to_entry(db, data.asset_ids, data.timeline_entry_id)
    return {"data": {"linked": len(data.asset_ids)}, "error": None}


@router.delete(
    "/incidents/{incident_id}/assets/{asset_id}/timeline-links/{entry_id}",
    status_code=204,
)
async def unlink_asset_from_entry(
    incident_id: str,
    asset_id: UUID,
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("assets.create")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    await asset_service.unlink_asset_from_entry(db, asset_id, entry_id)


@router.get("/incidents/{incident_id}/timeline/{entry_id}/assets")
async def list_entry_assets(
    incident_id: str,
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("assets.read")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    assets = await asset_service.list_entry_assets(db, entry_id)
    return {"data": [AssetOut.model_validate(a) for a in assets], "error": None}


# ── Asset-to-asset links ──────────────────────────────────────────────────────

@router.get("/incidents/{incident_id}/asset-links")
async def list_asset_links(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("assets.read")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    links = await asset_service.list_asset_links(db, incident_id)
    return {"data": [AssetLinkOut.model_validate(lnk) for lnk in links], "error": None}


@router.post("/incidents/{incident_id}/asset-links", status_code=201)
async def create_asset_link(
    incident_id: str,
    data: AssetLinkCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("assets.create")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    link = await asset_service.create_asset_link(db, incident_id, data, str(current_user.id))
    return {"data": AssetLinkOut.model_validate(link), "error": None}


@router.delete("/incidents/{incident_id}/asset-links/{link_id}", status_code=204)
async def delete_asset_link(
    incident_id: str,
    link_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("assets.delete")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    await asset_service.delete_asset_link(db, link_id, incident_id)
