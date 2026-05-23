"""
Incident service: CRUD, ref generation (INC-YYYY-NNNN), stats.
"""
from datetime import UTC, datetime

import bleach
from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.attachment import Attachment
from app.models.incident import Incident, IncidentExternalRef
from app.models.ioc import IOC
from app.models.task import Task
from app.models.template import IncidentTemplate
from app.models.timeline import TimelineEntry
from app.schemas.incident import IncidentCreate, IncidentStats, IncidentUpdate

_RICH_TEXT_TAGS = [
    "p", "br", "strong", "em", "u", "s", "b", "i",
    "h1", "h2", "h3", "ul", "ol", "li", "blockquote", "label",
]
_RICH_TEXT_ATTRS = {
    "ul": ["data-type"],
    "li": ["data-checked"],
}
_RICH_TEXT_FIELDS = {"executive_summary", "notes", "lessons_learned", "actions_todo"}


def _sanitize_html(value: str) -> str:
    return bleach.clean(value, tags=_RICH_TEXT_TAGS, attributes=_RICH_TEXT_ATTRS, strip=True)


async def generate_ref(db: AsyncSession, org_id: str) -> str:
    """
    Generates INC-YYYY-NNNN. Thread-safe via DB sequence.
    Uses a PostgreSQL sequence per org per year.
    """
    year = datetime.now(UTC).year
    seq_name = f"incident_seq_{str(org_id).replace('-', '_')}_{year}"

    # Create sequence if it doesn't exist
    await db.execute(
        text(f"CREATE SEQUENCE IF NOT EXISTS {seq_name} START 1")
    )
    result = await db.execute(text(f"SELECT nextval('{seq_name}')"))
    n = result.scalar()
    return f"INC-{year}-{n:04d}"


async def create_incident(
    db: AsyncSession,
    org_id: str,
    data: IncidentCreate,
    created_by: str | None = None,
    created_via: str = "ui",
    created_by_key_id: str | None = None,
) -> Incident:
    ref = await generate_ref(db, org_id)
    incident = Incident(
        org_id=org_id,
        incident_ref=ref,
        title=data.title,
        severity=data.severity,
        template_id=data.template_id,
        assigned_to=data.assigned_to,
        created_by=created_by,
    )
    db.add(incident)
    await db.flush()

    # Instantiate tasks from template
    if data.template_id:
        await _instantiate_template_tasks(db, incident.id, data.template_id)

    return incident


async def _instantiate_template_tasks(
    db: AsyncSession, incident_id: str, template_id: str
) -> None:
    result = await db.execute(
        select(IncidentTemplate).where(IncidentTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        return

    for i, task_def in enumerate(template.tasks_json or []):
        task = Task(
            incident_id=incident_id,
            template_id=template_id,
            title=task_def.get("title", "Untitled task"),
            description=task_def.get("description"),
            phase=task_def.get("phase"),
            priority=task_def.get("priority", "medium"),
            sort_order=i,
        )
        db.add(task)
    await db.flush()


async def get_incident(db: AsyncSession, incident_id: str, org_id: str) -> Incident:
    result = await db.execute(
        select(Incident)
        .options(selectinload(Incident.external_refs), selectinload(Incident.assigned_user))
        .where(Incident.id == incident_id, Incident.org_id == org_id)
    )
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident


async def list_incidents(
    db: AsyncSession,
    org_id: str,
    status_filter: str | None = None,
    severity_filter: str | None = None,
    search: str | None = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[Incident], int]:
    query = (
        select(Incident)
        .options(selectinload(Incident.external_refs), selectinload(Incident.assigned_user))
        .where(Incident.org_id == org_id)
    )
    if status_filter:
        query = query.where(Incident.status == status_filter)
    if severity_filter:
        query = query.where(Incident.severity == severity_filter)
    if search:
        query = query.where(Incident.title.ilike(f"%{search}%"))

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(Incident.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def update_incident(
    db: AsyncSession, incident: Incident, data: IncidentUpdate
) -> Incident:
    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        if key == "metadata":
            incident.metadata_ = value
        elif key in _RICH_TEXT_FIELDS and isinstance(value, str):
            setattr(incident, key, _sanitize_html(value))
        else:
            setattr(incident, key, value)

    # Set timestamps for status transitions
    now = datetime.now(UTC)
    if data.status == "contained" and not incident.contained_at:
        incident.contained_at = now
    if data.status == "closed" and not incident.closed_at:
        incident.closed_at = now

    await db.flush()
    await db.refresh(incident)
    return incident


async def delete_incident(db: AsyncSession, incident: Incident) -> None:
    await db.delete(incident)
    await db.flush()


async def get_stats(db: AsyncSession, incident_id: str) -> IncidentStats:
    timeline_count = (
        await db.execute(
            select(func.count()).select_from(TimelineEntry).where(TimelineEntry.incident_id == incident_id)
        )
    ).scalar() or 0

    ioc_count = (
        await db.execute(
            select(func.count()).select_from(IOC).where(IOC.incident_id == incident_id)
        )
    ).scalar() or 0

    task_result = await db.execute(
        select(Task.status).where(Task.incident_id == incident_id)
    )
    statuses = [r[0] for r in task_result.all()]
    task_total = len(statuses)
    task_done = sum(1 for s in statuses if s == "done")

    attachment_count = (
        await db.execute(
            select(func.count()).select_from(Attachment).where(Attachment.incident_id == incident_id)
        )
    ).scalar() or 0

    # Duration
    incident_result = await db.execute(
        select(Incident.opened_at, Incident.closed_at).where(Incident.id == incident_id)
    )
    row = incident_result.one_or_none()
    duration_hours = None
    if row and row.opened_at:
        end = row.closed_at or datetime.now(UTC)
        if row.opened_at.tzinfo is None:
            opened_at = row.opened_at.replace(tzinfo=UTC)
        else:
            opened_at = row.opened_at
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)
        duration_hours = (end - opened_at).total_seconds() / 3600

    return IncidentStats(
        timeline_count=timeline_count,
        ioc_count=ioc_count,
        task_total=task_total,
        task_done=task_done,
        attachment_count=attachment_count,
        duration_hours=duration_hours,
    )


async def add_external_ref(
    db: AsyncSession,
    incident_id: str,
    external_source: str,
    external_ref: str,
    external_url: str | None = None,
) -> IncidentExternalRef:
    ref = IncidentExternalRef(
        incident_id=incident_id,
        external_source=external_source,
        external_ref=external_ref,
        external_url=external_url,
    )
    db.add(ref)
    await db.flush()
    return ref
