"""
Report template extended endpoints — Phase 3.

Adds clone and preview on top of the basic CRUD in templates.py.

GET    /report-templates                       → list (system + org)
POST   /report-templates                       → create (premium)
GET    /report-templates/{id}                  → get with schema
PUT    /report-templates/{id}                  → update schema (premium)
DELETE /report-templates/{id}                  → delete org templates only
POST   /report-templates/{id}/clone            → clone → org copy
GET    /report-templates/{id}/preview          → rendered HTML preview
"""
import base64

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.feature_flags import check_feature
from app.core.permissions import require_permission
from app.schemas.template import ReportTemplateCreate, ReportTemplateOut, ReportTemplateUpdate
from app.services import template_service

_LOGO_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
_LOGO_MIME_MAP = {
    "image/png": "image/png",
    "image/jpeg": "image/jpeg",
    "image/svg+xml": "image/svg+xml",
}

router = APIRouter(tags=["report-templates"])


@router.get("/report-templates", response_model=list[ReportTemplateOut])
async def list_report_templates(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.read")),
):
    templates = await template_service.list_report_templates(db, str(current_user.org_id))
    return [ReportTemplateOut.model_validate(t) for t in templates]


@router.post("/report-templates", status_code=201)
async def create_report_template(
    data: ReportTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.create")),
):
    if not check_feature("report_template_builder"):
        raise HTTPException(status_code=402, detail="Report Template Builder requires a premium license")
    template = await template_service.create_report_template(
        db, str(current_user.org_id), data, str(current_user.id)
    )
    return {"data": ReportTemplateOut.model_validate(template), "error": None}


@router.get("/report-templates/{template_id}", response_model=ReportTemplateOut)
async def get_report_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.read")),
):
    template = await template_service.get_report_template(db, template_id, str(current_user.org_id))
    return ReportTemplateOut.model_validate(template)


@router.put("/report-templates/{template_id}")
async def update_report_template(
    template_id: str,
    data: ReportTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.update")),
):
    template = await template_service.get_report_template(db, template_id, str(current_user.org_id))
    updates = data.model_dump(exclude_none=True)
    is_hide_only = set(updates.keys()) <= {"is_hidden"}
    if not is_hide_only and not check_feature("report_template_builder"):
        raise HTTPException(status_code=402, detail="Report Template Builder requires a premium license")
    if template.is_system and not is_hide_only:
        raise HTTPException(status_code=403, detail="System templates are read-only — clone first")
    updated = await template_service.update_report_template(db, template, data)
    return {"data": ReportTemplateOut.model_validate(updated), "error": None}


@router.post("/report-templates/{template_id}/logo")
async def upload_template_logo(
    template_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.update")),
):
    """Accept PNG/JPEG/SVG logo, convert to base64 data URI, store on template."""
    content_type = file.content_type or ""
    mime = _LOGO_MIME_MAP.get(content_type)
    if not mime:
        raise HTTPException(status_code=400, detail="Only PNG, JPEG, or SVG logos are accepted")

    logo_bytes = await file.read()
    if len(logo_bytes) > _LOGO_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Logo too large (max 2 MB)")

    data_uri = f"data:{mime};base64,{base64.b64encode(logo_bytes).decode()}"

    template = await template_service.get_report_template(db, template_id, str(current_user.org_id))
    if template.is_system:
        raise HTTPException(status_code=403, detail="System templates are read-only — clone first")

    template.logo_data_uri = data_uri
    await db.commit()
    await db.refresh(template)
    return {"data": ReportTemplateOut.model_validate(template), "error": None}


@router.delete("/report-templates/{template_id}", status_code=204)
async def delete_report_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.delete")),
):
    template = await template_service.get_report_template(db, template_id, str(current_user.org_id))
    if template.is_system:
        raise HTTPException(status_code=403, detail="System templates cannot be deleted")
    await template_service.delete_report_template(db, template)


@router.post("/report-templates/{template_id}/clone", status_code=201)
async def clone_report_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.create")),
):
    """Clone a template (typically a system one) into the org's own copy."""
    source = await template_service.get_report_template(db, template_id, str(current_user.org_id))
    cloned = await template_service.clone_report_template(
        db, source, str(current_user.org_id), str(current_user.id)
    )
    return {"data": ReportTemplateOut.model_validate(cloned), "error": None}


@router.get("/report-templates/{template_id}/preview")
async def preview_report_template(
    template_id: str,
    incident_id: str = Query(..., description="Incident ID to preview against"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports.generate")),
):
    """Render the template as HTML using a real incident's data."""
    from app.models.user import User
    from app.services.report_renderer import build_report_payload
    from app.services.report_renderer.fixed_report import render_fixed_report_html, render_from_schema
    from sqlalchemy import select

    template = await template_service.get_report_template(db, template_id, str(current_user.org_id))

    result = await db.execute(select(User).where(User.id == current_user.id))
    analyst = result.scalar_one()

    payload = await build_report_payload(
        incident_id=incident_id,
        analyst=analyst,
        db=db,
    )

    if template.schema_json:
        brand = {
            "logo_data_uri": template.logo_data_uri,
            "primary_colour": template.primary_colour or "#F97316",
            "company_name": template.company_name,
        }
        html = render_from_schema(payload, template.schema_json, brand)
    else:
        html = render_fixed_report_html(payload)
    return HTMLResponse(content=html)
