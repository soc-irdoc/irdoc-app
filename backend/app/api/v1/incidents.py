from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.core.security import get_current_user
from app.schemas.common import Meta
from app.schemas.incident import (
    ExternalRefCreate,
    ExternalRefOut,
    IncidentCreate,
    IncidentOut,
    IncidentStats,
    IncidentUpdate,
)
from app.services import incident_service
from app.sio import publish_ws

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("")
async def list_incidents(
    status: str | None = Query(None),
    severity: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("incidents.read")),
):
    incidents, total = await incident_service.list_incidents(
        db,
        org_id=str(current_user.org_id),
        status_filter=status,
        severity_filter=severity,
        search=search,
        page=page,
        per_page=per_page,
    )
    return {
        "data": [IncidentOut.model_validate(i) for i in incidents],
        "meta": Meta(page=page, per_page=per_page, total=total),
        "error": None,
    }


@router.post("", status_code=201)
async def create_incident(
    data: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("incidents.create")),
):
    incident = await incident_service.create_incident(
        db, str(current_user.org_id), data, created_by=str(current_user.id)
    )
    return {"data": IncidentOut.model_validate(incident), "error": None}


@router.get("/{incident_id}")
async def get_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("incidents.read")),
):
    incident = await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    return {"data": IncidentOut.model_validate(incident), "error": None}


@router.put("/{incident_id}")
async def update_incident(
    incident_id: str,
    data: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("incidents.update")),
):
    incident = await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    updated = await incident_service.update_incident(db, incident, data)
    out = IncidentOut.model_validate(updated)
    await publish_ws(incident_id, "incident:updated", out.model_dump(mode="json"))

    from app.services.report_service import maybe_trigger_ai_report, maybe_trigger_sharepoint_sync
    await maybe_trigger_ai_report(db, incident_id, str(current_user.org_id))
    await maybe_trigger_sharepoint_sync(db, incident_id, str(current_user.org_id))

    return {"data": out, "error": None}


@router.delete("/{incident_id}", status_code=204)
async def delete_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("incidents.delete")),
):
    incident = await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    await incident_service.delete_incident(db, incident)


@router.get("/{incident_id}/stats", response_model=IncidentStats)
async def get_incident_stats(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("incidents.read")),
):
    # Verify access
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    return await incident_service.get_stats(db, incident_id)


@router.get("/{incident_id}/external-refs", response_model=list[ExternalRefOut])
async def list_external_refs(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("incidents.read")),
):
    incident = await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    return [ExternalRefOut.model_validate(r) for r in incident.external_refs]


@router.post("/{incident_id}/external-refs", status_code=201)
async def add_external_ref(
    incident_id: str,
    data: ExternalRefCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("incidents.update")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    ref = await incident_service.add_external_ref(
        db, incident_id, data.external_source, data.external_ref, data.external_url
    )
    return {"data": ExternalRefOut.model_validate(ref), "error": None}
