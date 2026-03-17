"""
Template service: incident templates + report templates.
System templates (org_id=null) are read-only — orgs must clone.
"""
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.template import IncidentTemplate, ReportTemplate
from app.schemas.template import (
    IncidentTemplateCreate,
    IncidentTemplateUpdate,
    ReportTemplateCreate,
    ReportTemplateUpdate,
)


# ─── Incident Templates ─────────────────────────────────────────────────────────

async def list_incident_templates(db: AsyncSession, org_id: str) -> list[IncidentTemplate]:
    result = await db.execute(
        select(IncidentTemplate).where(
            (IncidentTemplate.org_id == org_id) | (IncidentTemplate.org_id == None)  # noqa: E711
        )
    )
    return list(result.scalars().all())


async def get_incident_template(db: AsyncSession, template_id: str, org_id: str) -> IncidentTemplate:
    result = await db.execute(
        select(IncidentTemplate).where(
            IncidentTemplate.id == template_id,
            (IncidentTemplate.org_id == org_id) | (IncidentTemplate.org_id == None),  # noqa: E711
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template


async def create_incident_template(
    db: AsyncSession, org_id: str, data: IncidentTemplateCreate
) -> IncidentTemplate:
    template = IncidentTemplate(
        org_id=org_id,
        name=data.name,
        slug=data.slug,
        description=data.description,
        tasks_json=data.tasks_json,
        is_system=False,
    )
    db.add(template)
    await db.flush()
    return template


async def update_incident_template(
    db: AsyncSession, template: IncidentTemplate, data: IncidentTemplateUpdate
) -> IncidentTemplate:
    if template.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System templates are read-only. Clone to customize.",
        )
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(template, key, value)
    await db.flush()
    return template


async def delete_incident_template(db: AsyncSession, template: IncidentTemplate) -> None:
    if template.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System templates cannot be deleted.",
        )
    await db.delete(template)
    await db.flush()


# ─── Report Templates ───────────────────────────────────────────────────────────

async def list_report_templates(db: AsyncSession, org_id: str) -> list[ReportTemplate]:
    result = await db.execute(
        select(ReportTemplate).where(
            (ReportTemplate.org_id == org_id) | (ReportTemplate.org_id == None)  # noqa: E711
        )
    )
    return list(result.scalars().all())


async def get_report_template(db: AsyncSession, template_id: str, org_id: str) -> ReportTemplate:
    result = await db.execute(
        select(ReportTemplate).where(
            ReportTemplate.id == template_id,
            (ReportTemplate.org_id == org_id) | (ReportTemplate.org_id == None),  # noqa: E711
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report template not found")
    return template


async def create_report_template(
    db: AsyncSession, org_id: str, data: ReportTemplateCreate, created_by: str | None = None
) -> ReportTemplate:
    template = ReportTemplate(
        org_id=org_id,
        name=data.name,
        destination=data.destination,
        description=data.description,
        schema_json=data.schema_json,
        created_by=created_by,
        is_system=False,
    )
    db.add(template)
    await db.flush()
    return template


async def update_report_template(
    db: AsyncSession, template: ReportTemplate, data: ReportTemplateUpdate
) -> ReportTemplate:
    if template.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System templates are read-only. Clone to customize.",
        )
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(template, key, value)
    await db.flush()
    return template


async def delete_report_template(db: AsyncSession, template: ReportTemplate) -> None:
    if template.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System templates cannot be deleted.",
        )
    await db.delete(template)
    await db.flush()


async def clone_report_template(
    db: AsyncSession,
    source: ReportTemplate,
    org_id: str,
    created_by: str | None = None,
) -> ReportTemplate:
    """Clone a template (usually a system one) into the org's own editable copy."""
    cloned = ReportTemplate(
        org_id=org_id,
        name=f"{source.name} (Copy)",
        destination=source.destination,
        description=source.description,
        schema_json=list(source.schema_json),  # deep copy of list
        created_by=created_by,
        is_system=False,
        is_default=False,
    )
    db.add(cloned)
    await db.commit()
    await db.refresh(cloned)
    return cloned
