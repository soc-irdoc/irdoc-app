"""
Report endpoints — Phase 3.

POST   /incidents/{id}/reports          → enqueue generation
GET    /incidents/{id}/reports          → list generated reports
GET    /reports/{id}                    → status + metadata
GET    /reports/{id}/download           → stream file
DELETE /reports/{id}                    → delete report
"""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.schemas.report import ReportGenerateRequest, ReportOut
from app.services import report_service

router = APIRouter(tags=["reports"])


@router.post("/incidents/{incident_id}/reports", status_code=202)
async def enqueue_report(
    incident_id: str,
    request: ReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports.generate")),
):
    report = await report_service.enqueue_report(
        db=db,
        incident_id=incident_id,
        request=request,
        generated_by=str(current_user.id),
        org_id=str(current_user.org_id),
    )
    return {"data": ReportOut.model_validate(report), "error": None}


@router.get("/incidents/{incident_id}/reports")
async def list_reports(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports.read")),
):
    reports = await report_service.list_reports(db, incident_id)
    return {
        "data": [ReportOut.model_validate(r) for r in reports],
        "meta": {"total": len(reports)},
        "error": None,
    }


@router.get("/reports/{report_id}", response_model=ReportOut)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports.read")),
):
    report = await report_service.get_report(db, report_id)
    return ReportOut.model_validate(report)


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports.read")),
):
    from fastapi import HTTPException
    from app.services.storage.resolver import get_storage_backend

    report = await report_service.get_report(db, report_id)
    if report.status != "ready" or not report.storage_path:
        raise HTTPException(status_code=404, detail="Report not ready or file not found")

    backend = get_storage_backend()
    file_bytes = await backend.retrieve(report.storage_path)

    mime_map = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "markdown": "text/markdown",
        "html": "text/html",
    }
    content_type = mime_map.get(report.format, "application/octet-stream")
    ext_map = {"pdf": "pdf", "docx": "docx", "markdown": "md", "html": "html"}
    ext = ext_map.get(report.format, "bin")
    filename = f"{report.report_type.replace(' ', '_')}_{report_id[:8]}.{ext}"

    import io
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/reports/{report_id}", status_code=204)
async def delete_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports.generate")),
):
    report = await report_service.get_report(db, report_id)
    await report_service.delete_report(db, report)
