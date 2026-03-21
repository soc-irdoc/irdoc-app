"""
DOCX Template endpoints.

GET    /docx-templates           → list org's templates
GET    /docx-templates/base      → download the base template scaffold
POST   /docx-templates           → upload a custom template (multipart)
PATCH  /docx-templates/{id}      → rename
POST   /docx-templates/{id}/set-default  → set as org default
DELETE /docx-templates/{id}      → delete
"""
import io

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.schemas.docx_template import DocxTemplateOut, DocxTemplateRename
from app.services import docx_template_service

router = APIRouter(tags=["docx_templates"])

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.get("/docx-templates")
async def list_docx_templates(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports.read")),
):
    templates = await docx_template_service.list_templates(str(current_user.org_id), db)
    return {
        "data": [DocxTemplateOut.model_validate(t) for t in templates],
        "meta": {"total": len(templates)},
        "error": None,
    }


@router.get("/docx-templates/base")
async def download_base_template(
    current_user=Depends(require_permission("reports.read")),
):
    """Download the base DOCX scaffold with all placeholder markers."""
    file_bytes = docx_template_service.generate_base_template()
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=DOCX_MIME,
        headers={"Content-Disposition": 'attachment; filename="irdoc_base_template.docx"'},
    )


@router.post("/docx-templates", status_code=201)
async def upload_docx_template(
    name: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.create")),
):
    """Upload a customised DOCX template."""
    from fastapi import HTTPException

    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are accepted")

    file_bytes = await file.read()
    if len(file_bytes) > 20 * 1024 * 1024:  # 20 MB max
        raise HTTPException(status_code=413, detail="File too large (max 20 MB)")

    # Validate it's a real docx
    try:
        import io as _io
        from docx import Document
        Document(_io.BytesIO(file_bytes))
    except Exception:
        raise HTTPException(status_code=400, detail="File is not a valid .docx document")

    t = await docx_template_service.create_template(
        org_id=str(current_user.org_id),
        name=name,
        file_bytes=file_bytes,
        file_size=len(file_bytes),
        created_by=str(current_user.id),
        db=db,
    )
    return {"data": DocxTemplateOut.model_validate(t), "error": None}


@router.patch("/docx-templates/{template_id}")
async def rename_docx_template(
    template_id: str,
    body: DocxTemplateRename,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.create")),
):
    t = await docx_template_service.rename_template(
        template_id, str(current_user.org_id), body.name, db
    )
    return {"data": DocxTemplateOut.model_validate(t), "error": None}


@router.post("/docx-templates/{template_id}/set-default")
async def set_default_docx_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.create")),
):
    t = await docx_template_service.set_default(
        template_id, str(current_user.org_id), db
    )
    return {"data": DocxTemplateOut.model_validate(t), "error": None}


@router.delete("/docx-templates/{template_id}", status_code=204)
async def delete_docx_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.delete")),
):
    await docx_template_service.delete_template(
        template_id, str(current_user.org_id), db
    )
