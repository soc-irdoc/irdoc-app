"""Evidence register (#150): read-only list of what an incident has collected.

No upload or delete here; files are still added through timeline entries.
"""
import io
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import has_permission, require_permission
from app.schemas.common import Meta
from app.schemas.evidence import EvidenceKind, EvidenceSort
from app.services import audit_service, evidence_service, incident_service

router = APIRouter(tags=["evidence"])


def _filters(
    kind: EvidenceKind | None = Query(None),
    mime: str | None = Query(None, max_length=100),
    q: str | None = Query(None, max_length=200),
    hide_screenshots: bool = Query(False),
) -> evidence_service.EvidenceFilters:
    return evidence_service.EvidenceFilters(kind=kind, mime=mime, q=q, hide_screenshots=hide_screenshots)


@router.get("/incidents/{incident_id}/evidence")
async def list_evidence(
    incident_id: str,
    filters: evidence_service.EvidenceFilters = Depends(_filters),
    sort: EvidenceSort = Query("uploaded_at"),
    order: Literal["asc", "desc"] = Query("desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("attachments.read")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    files, total = await evidence_service.list_files(
        db, incident_id, filters, sort=sort, order=order, page=page, per_page=per_page,
        # Chips reveal assets / IOCs, so only for users who may read them.
        include_assets=has_permission(current_user.role, "assets.read"),
        include_iocs=has_permission(current_user.role, "iocs.read"),
    )
    return {"data": files, "meta": Meta(page=page, per_page=per_page, total=total), "error": None}


@router.get("/incidents/{incident_id}/evidence/iocs")
async def list_evidence_iocs(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("iocs.read")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    return {"data": await evidence_service.list_iocs(db, incident_id), "error": None}


@router.get("/incidents/{incident_id}/evidence/export.csv")
async def export_evidence_csv(
    request: Request,
    incident_id: str,
    filters: evidence_service.EvidenceFilters = Depends(_filters),
    sort: EvidenceSort = Query("uploaded_at"),
    order: Literal["asc", "desc"] = Query("desc"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("attachments.read")),
):
    incident = await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    files = await evidence_service.all_files(
        db, incident_id, filters, sort=sort, order=order,
        include_iocs=has_permission(current_user.role, "iocs.read"),
    )
    await audit_service.log(
        db,
        org_id=str(current_user.org_id),
        action="evidence.exported",
        entity_type="incident",
        entity_id=str(incident.id),
        actor_label=current_user.email,
        entity_label=f"{incident.incident_ref} - {incident.title}",
        diff={"files": len(files)},
        user_id=str(current_user.id),
        request=request,
    )
    filename = f"{incident.incident_ref}-evidence.csv"
    return StreamingResponse(
        io.StringIO(evidence_service.export_csv(files)),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
