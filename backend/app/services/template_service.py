"""
Template service: incident templates + report templates.
System templates (org_id=null) are read-only - orgs must clone.
"""
import copy

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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


async def _ensure_slug_available(
    db: AsyncSession, org_id: str, slug: str, exclude_id=None
) -> None:
    """409 unless `slug` is free among the org's own templates and the system
    templates, so every slug an org can see points to exactly one template (#168)."""
    query = select(IncidentTemplate).where(
        IncidentTemplate.slug == slug,
        (IncidentTemplate.org_id == org_id) | (IncidentTemplate.org_id == None),  # noqa: E711
    )
    if exclude_id is not None:
        query = query.where(IncidentTemplate.id != exclude_id)
    clash = (await db.execute(query.limit(1))).scalar_one_or_none()
    if clash is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Slug '{slug}' is already used by template '{clash.name}'",
        )


async def _flush_or_409(db: AsyncSession, slug: str) -> None:
    """Flush, turning a lost race on uq_incident_templates_org_slug into 409."""
    try:
        async with db.begin_nested():
            await db.flush()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Slug '{slug}' is already used by another template",
        ) from None


async def create_incident_template(
    db: AsyncSession, org_id: str, data: IncidentTemplateCreate
) -> IncidentTemplate:
    await _ensure_slug_available(db, org_id, data.slug)
    template = IncidentTemplate(
        org_id=org_id,
        name=data.name,
        slug=data.slug,
        description=data.description,
        tasks_json=data.tasks_json,
        is_system=False,
    )
    db.add(template)
    await _flush_or_409(db, data.slug)
    await db.refresh(template)
    return template


async def update_incident_template(
    db: AsyncSession, template: IncidentTemplate, data: IncidentTemplateUpdate
) -> IncidentTemplate:
    updates = data.model_dump(exclude_none=True)
    # Re-sending the current slug (the edit form always does) is not a change.
    if updates.get("slug") == template.slug:
        updates.pop("slug")
    if template.is_system and set(updates.keys()) - {"is_hidden"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System templates are read-only. Clone to customize.",
        )
    if "slug" in updates:
        await _ensure_slug_available(db, str(template.org_id), updates["slug"], exclude_id=template.id)
    for key, value in updates.items():
        setattr(template, key, value)
    await _flush_or_409(db, template.slug)
    await db.refresh(template)
    return template


async def delete_incident_template(db: AsyncSession, template: IncidentTemplate) -> None:
    if template.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System templates cannot be deleted.",
        )
    await db.delete(template)
    await db.flush()


async def _free_copy_slug(db: AsyncSession, org_id: str, base: str) -> str:
    """`<base>-copy`, then `-copy-2`, `-copy-3`, ...: the first one free."""
    stem = f"{base[:90]}-copy"
    taken = set((await db.execute(
        select(IncidentTemplate.slug).where(
            IncidentTemplate.slug.like(f"{stem}%"),
            (IncidentTemplate.org_id == org_id) | (IncidentTemplate.org_id == None),  # noqa: E711
        )
    )).scalars())
    if stem not in taken:
        return stem
    n = 2
    while f"{stem}-{n}" in taken:
        n += 1
    return f"{stem}-{n}"


async def clone_incident_template(
    db: AsyncSession, source: IncidentTemplate, org_id: str
) -> IncidentTemplate:
    """Clone a template (usually a system one) into the org's own editable copy."""
    slug = await _free_copy_slug(db, org_id, source.slug)
    cloned = IncidentTemplate(
        org_id=org_id,
        name=f"{source.name} (Copy)",
        slug=slug,
        description=source.description,
        tasks_json=copy.deepcopy(source.tasks_json or []),
        is_system=False,
        is_hidden=False,
    )
    db.add(cloned)
    await _flush_or_409(db, slug)
    await db.refresh(cloned)
    return cloned


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
    await db.refresh(template)
    return template


async def update_report_template(
    db: AsyncSession, template: ReportTemplate, data: ReportTemplateUpdate
) -> ReportTemplate:
    updates = data.model_dump(exclude_none=True)
    if template.is_system and set(updates.keys()) - {"is_hidden"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System templates are read-only. Clone to customize.",
        )
    for key, value in updates.items():
        # Assign a new list object for JSONB columns to ensure SQLAlchemy detects the change
        setattr(template, key, list(value) if isinstance(value, list) else value)
    await db.flush()
    await db.refresh(template)
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
