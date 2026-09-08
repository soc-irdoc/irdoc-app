import io

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.schemas.common import Meta
from app.schemas.timeline import TimelineEntryCreate, TimelineEntryOut, TimelineEntryUpdate
from app.services import audit_service, incident_service, timeline_service
from app.sio import publish_ws
from app.workers import tasks as worker_tasks

router = APIRouter(tags=["timeline"])


def _route(prefix: str) -> APIRouter:
    return APIRouter(prefix=f"/incidents/{prefix}/timeline")


@router.get("/incidents/{incident_id}/timeline")
async def list_timeline(
    incident_id: str,
    entry_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("timeline.read")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    entries, total = await timeline_service.list_entries(
        db, incident_id, entry_type=entry_type, page=page, per_page=per_page
    )
    return {
        "data": [TimelineEntryOut.model_validate(e) for e in entries],
        "meta": Meta(page=page, per_page=per_page, total=total),
        "error": None,
    }


@router.post("/incidents/{incident_id}/timeline", status_code=201)
async def create_timeline_entry(
    request: Request,
    incident_id: str,
    data: TimelineEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("timeline.create")),
):
    incident = await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    entry = await timeline_service.create_entry(db, incident_id, data, str(current_user.id))

    # Async: scan for IOC suggestions
    try:
        worker_tasks.auto_detect_iocs_from_entry.delay(str(entry.id))
    except Exception as exc:
        # Celery broker unavailable (e.g., Redis not running in test env) — best-effort dispatch
        import logging
        logging.getLogger(__name__).debug("Failed to dispatch IOC detection task: %s", exc)

    await audit_service.log(
        db,
        org_id=str(current_user.org_id),
        action="incident.comment_added",
        entity_type="incident",
        entity_id=str(incident_id),
        actor_label=current_user.email,
        entity_label=f"{incident.incident_ref} — {incident.title}",
        user_id=str(current_user.id),
        request=request,
    )

    out = TimelineEntryOut.model_validate(entry)
    await publish_ws(incident_id, "timeline:entry:added", out.model_dump(mode="json"))

    from app.services.report_service import maybe_trigger_ai_report, maybe_trigger_sharepoint_sync
    await maybe_trigger_ai_report(db, incident_id, str(current_user.org_id))
    await maybe_trigger_sharepoint_sync(db, incident_id, str(current_user.org_id))
    return {"data": out, "error": None}


@router.put("/incidents/{incident_id}/timeline/{entry_id}")
async def update_timeline_entry(
    incident_id: str,
    entry_id: str,
    data: TimelineEntryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("timeline.create")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    entry = await timeline_service.get_entry(db, entry_id, incident_id)
    updated = await timeline_service.update_entry(db, entry, data)
    out = TimelineEntryOut.model_validate(updated)
    await publish_ws(incident_id, "timeline:entry:updated", out.model_dump(mode="json"))

    from app.services.report_service import maybe_trigger_ai_report, maybe_trigger_sharepoint_sync
    await maybe_trigger_ai_report(db, incident_id, str(current_user.org_id))
    await maybe_trigger_sharepoint_sync(db, incident_id, str(current_user.org_id))
    return {"data": out, "error": None}


@router.delete("/incidents/{incident_id}/timeline/{entry_id}", status_code=204)
async def delete_timeline_entry(
    incident_id: str,
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("timeline.delete_any")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    entry = await timeline_service.get_entry(db, entry_id, incident_id)
    await timeline_service.delete_entry(db, entry)
    await publish_ws(incident_id, "timeline:entry:deleted", {"id": entry_id})


@router.post("/incidents/{incident_id}/timeline/{entry_id}/pin")
async def pin_timeline_entry(
    incident_id: str,
    entry_id: str,
    pinned: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("timeline.pin")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    entry = await timeline_service.get_entry(db, entry_id, incident_id)
    updated = await timeline_service.pin_entry(db, entry, pinned)
    return {"data": TimelineEntryOut.model_validate(updated), "error": None}


@router.get("/incidents/{incident_id}/timeline/export/csv")
async def export_timeline_csv(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("timeline.read")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    entries, _ = await timeline_service.list_entries(db, incident_id, per_page=10000)
    csv_content = timeline_service.export_csv(entries)
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="timeline_{incident_id}.csv"'},
    )
