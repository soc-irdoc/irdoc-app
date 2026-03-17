from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.schemas.template import (
    IncidentTemplateCreate,
    IncidentTemplateOut,
    IncidentTemplateUpdate,
    ReportTemplateCreate,
    ReportTemplateOut,
    ReportTemplateUpdate,
)
from app.services import template_service

router = APIRouter(tags=["templates"])


# ─── Incident Templates ─────────────────────────────────────────────────────────

@router.get("/templates/incident", response_model=list[IncidentTemplateOut])
async def list_incident_templates(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.read")),
):
    templates = await template_service.list_incident_templates(db, str(current_user.org_id))
    return [IncidentTemplateOut.model_validate(t) for t in templates]


@router.post("/templates/incident", status_code=201)
async def create_incident_template(
    data: IncidentTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.create")),
):
    template = await template_service.create_incident_template(db, str(current_user.org_id), data)
    return {"data": IncidentTemplateOut.model_validate(template), "error": None}


@router.put("/templates/incident/{template_id}")
async def update_incident_template(
    template_id: str,
    data: IncidentTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.update")),
):
    template = await template_service.get_incident_template(db, template_id, str(current_user.org_id))
    updated = await template_service.update_incident_template(db, template, data)
    return {"data": IncidentTemplateOut.model_validate(updated), "error": None}


@router.delete("/templates/incident/{template_id}", status_code=204)
async def delete_incident_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.delete")),
):
    template = await template_service.get_incident_template(db, template_id, str(current_user.org_id))
    await template_service.delete_incident_template(db, template)


# ─── Report Templates ───────────────────────────────────────────────────────────

@router.get("/templates/report", response_model=list[ReportTemplateOut])
async def list_report_templates(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.read")),
):
    templates = await template_service.list_report_templates(db, str(current_user.org_id))
    return [ReportTemplateOut.model_validate(t) for t in templates]


@router.post("/templates/report", status_code=201)
async def create_report_template(
    data: ReportTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.create")),
):
    template = await template_service.create_report_template(
        db, str(current_user.org_id), data, str(current_user.id)
    )
    return {"data": ReportTemplateOut.model_validate(template), "error": None}


@router.put("/templates/report/{template_id}")
async def update_report_template(
    template_id: str,
    data: ReportTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.update")),
):
    template = await template_service.get_report_template(db, template_id, str(current_user.org_id))
    updated = await template_service.update_report_template(db, template, data)
    return {"data": ReportTemplateOut.model_validate(updated), "error": None}


@router.delete("/templates/report/{template_id}", status_code=204)
async def delete_report_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("templates.delete")),
):
    template = await template_service.get_report_template(db, template_id, str(current_user.org_id))
    await template_service.delete_report_template(db, template)
