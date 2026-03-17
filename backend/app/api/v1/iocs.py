from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.schemas.ioc import IOCBulkImport, IOCCreate, IOCDetected, IOCOut, IOCUpdate
from app.services import incident_service, ioc_service

router = APIRouter(tags=["iocs"])


@router.get("/incidents/{incident_id}/iocs")
async def list_iocs(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("iocs.read")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    iocs = await ioc_service.list_iocs(db, incident_id)
    return {"data": [IOCOut.model_validate(i) for i in iocs], "error": None}


@router.post("/incidents/{incident_id}/iocs", status_code=201)
async def create_ioc(
    incident_id: str,
    data: IOCCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("iocs.create")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    ioc = await ioc_service.create_ioc(db, incident_id, data, str(current_user.id))
    return {"data": IOCOut.model_validate(ioc), "error": None}


@router.post("/incidents/{incident_id}/iocs/bulk", status_code=201)
async def bulk_import_iocs(
    incident_id: str,
    data: IOCBulkImport,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("iocs.create")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    iocs = await ioc_service.bulk_import(db, incident_id, data.text, str(current_user.id))
    return {"data": [IOCOut.model_validate(i) for i in iocs], "error": None}


@router.post("/incidents/{incident_id}/iocs/detect", response_model=list[IOCDetected])
async def detect_iocs(
    incident_id: str,
    data: IOCBulkImport,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("iocs.read")),
):
    """Detect IOCs in text without saving. Used by the auto-detect modal."""
    return ioc_service.auto_detect(data.text)


@router.put("/incidents/{incident_id}/iocs/{ioc_id}")
async def update_ioc(
    incident_id: str,
    ioc_id: str,
    data: IOCUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("iocs.update")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    ioc = await ioc_service.get_ioc(db, ioc_id, incident_id)
    updated = await ioc_service.update_ioc(db, ioc, data)
    return {"data": IOCOut.model_validate(updated), "error": None}


@router.delete("/incidents/{incident_id}/iocs/{ioc_id}", status_code=204)
async def delete_ioc(
    incident_id: str,
    ioc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("iocs.delete")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    ioc = await ioc_service.get_ioc(db, ioc_id, incident_id)
    await ioc_service.delete_ioc(db, ioc)


@router.post("/iocs/{ioc_id}/enrich", status_code=202)
async def enrich_ioc(
    ioc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("iocs.create")),
):
    """Manually trigger re-enrichment for an IOC. Enqueues Celery task."""
    from app.workers.tasks import enrich_ioc as enrich_task
    enrich_task.delay(ioc_id)
    return {"data": {"ioc_id": ioc_id, "status": "enrichment_queued"}, "meta": {}, "error": None}


@router.post("/iocs/{ioc_id}/ai/narrative", status_code=202)
async def ioc_ai_narrative(
    ioc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("iocs.create")),
):
    """Generate an AI plain-English enrichment narrative for an IOC (premium)."""
    from app.core.feature_flags import check_feature
    from fastapi import HTTPException
    if not check_feature("ai_summaries"):
        raise HTTPException(status_code=403, detail="AI narratives require premium plan")
    from app.workers.tasks import generate_ai_ioc_narrative
    generate_ai_ioc_narrative.delay(ioc_id)
    return {"data": {"ioc_id": ioc_id, "status": "narrative_queued"}, "meta": {}, "error": None}
