from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.core.security import verify_file_token
from app.schemas.attachment import AttachmentOut, AttachmentURLResponse
from app.schemas.evidence import TextPreviewOut
from app.services import attachment_service, incident_service, report_regen_service
from app.services.storage.resolver import get_storage_backend

router = APIRouter(tags=["attachments"])


@router.post("/incidents/{incident_id}/attachments", status_code=201)
async def upload_attachment(
    incident_id: str,
    file: UploadFile = File(...),
    timeline_entry_id: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("attachments.upload")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    attachment = await attachment_service.upload_attachment(
        db,
        org_id=str(current_user.org_id),
        incident_id=incident_id,
        file=file,
        timeline_entry_id=timeline_entry_id,
        uploaded_by=str(current_user.id),
    )
    # Fire async hash verification
    from app.workers import tasks as worker_tasks
    worker_tasks.verify_file_hash.delay(str(attachment.id))
    await report_regen_service.maybe_trigger_report_regen(db, incident_id, str(current_user.org_id))

    return {"data": AttachmentOut.model_validate(attachment), "error": None}


@router.get("/incidents/{incident_id}/attachments/{attachment_id}/url")
async def get_attachment_url(
    incident_id: str,
    attachment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("attachments.read")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    attachment = await attachment_service.get_attachment(db, attachment_id, incident_id)
    url = await attachment_service.get_attachment_url(attachment)
    return {"data": AttachmentURLResponse(url=url, expires_in=3600), "error": None}


@router.get("/incidents/{incident_id}/attachments/{attachment_id}/text")
async def get_attachment_text(
    incident_id: str,
    attachment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("attachments.read")),
):
    """Plain-text preview (#150), returned as JSON so the browser never renders it as HTML.

    Served by the API rather than a storage URL because cloud backends give
    cross-origin URLs that the app's CSP (connect-src 'self') won't fetch.
    """
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    attachment = await attachment_service.get_attachment(db, attachment_id, incident_id)
    text, truncated = await attachment_service.get_text_preview(attachment)
    return {"data": TextPreviewOut(text=text, truncated=truncated), "error": None}


@router.delete("/incidents/{incident_id}/attachments/{attachment_id}", status_code=204)
async def delete_attachment(
    incident_id: str,
    attachment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("attachments.delete")),
):
    await incident_service.get_incident(db, incident_id, str(current_user.org_id))
    attachment = await attachment_service.get_attachment(db, attachment_id, incident_id)
    await attachment_service.delete_attachment(db, attachment)
    await report_regen_service.maybe_trigger_report_regen(db, incident_id, str(current_user.org_id))


@router.get("/files/{token}")
async def serve_file(token: str):
    """Serve files via signed token - never directly from web root."""
    path = verify_file_token(token)
    if not path:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired file token")

    backend = get_storage_backend()
    data = await backend.retrieve(path)

    # Guess content type
    import mimetypes
    content_type, _ = mimetypes.guess_type(path)
    return Response(content=data, media_type=content_type or "application/octet-stream")
