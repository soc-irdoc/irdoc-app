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
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.feature_flags import check_feature
from app.core.permissions import require_permission
from app.schemas.template import ReportTemplateCreate, ReportTemplateOut, ReportTemplateUpdate
from app.services import template_service

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
    if not check_feature("report_template_builder"):
        raise HTTPException(status_code=402, detail="Report Template Builder requires a premium license")
    template = await template_service.get_report_template(db, template_id, str(current_user.org_id))
    if template.is_system:
        raise HTTPException(status_code=403, detail="System templates are read-only — clone first")
    updated = await template_service.update_report_template(db, template, data)
    return {"data": ReportTemplateOut.model_validate(updated), "error": None}


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
    from app.services.report_renderer.fixed_report import render_fixed_report_html
    from sqlalchemy import select

    await template_service.get_report_template(db, template_id, str(current_user.org_id))

    result = await db.execute(select(User).where(User.id == current_user.id))
    analyst = result.scalar_one()

    payload = await build_report_payload(
        incident_id=incident_id,
        analyst=analyst,
        db=db,
    )

    html = render_fixed_report_html(payload)
    return HTMLResponse(content=html)
