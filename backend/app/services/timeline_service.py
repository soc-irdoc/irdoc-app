"""
Timeline service: CRUD + IOC mention auto-linking + CSV export.
"""
import csv
import io

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.timeline import TimelineEntry
from app.schemas.timeline import TimelineEntryCreate, TimelineEntryUpdate


async def create_entry(
    db: AsyncSession,
    incident_id: str,
    data: TimelineEntryCreate,
    author_id: str | None = None,
) -> TimelineEntry:
    entry = TimelineEntry(
        incident_id=incident_id,
        author_id=author_id,
        entry_type=data.entry_type,
        occurred_at=data.occurred_at,
        description=data.description,
        source=data.source,
        is_pinned=data.is_pinned,
        metadata_=data.metadata,
    )
    db.add(entry)
    await db.flush()
    return entry


async def list_entries(
    db: AsyncSession,
    incident_id: str,
    entry_type: str | None = None,
    page: int = 1,
    per_page: int = 100,
) -> tuple[list[TimelineEntry], int]:
    from sqlalchemy import func

    query = (
        select(TimelineEntry)
        .options(selectinload(TimelineEntry.attachments))
        .where(TimelineEntry.incident_id == incident_id)
    )
    if entry_type:
        query = query.where(TimelineEntry.entry_type == entry_type)

    from sqlalchemy import func
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(TimelineEntry.occurred_at.asc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def get_entry(
    db: AsyncSession, entry_id: str, incident_id: str
) -> TimelineEntry:
    result = await db.execute(
        select(TimelineEntry)
        .options(selectinload(TimelineEntry.attachments))
        .where(TimelineEntry.id == entry_id, TimelineEntry.incident_id == incident_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline entry not found")
    return entry


async def update_entry(
    db: AsyncSession, entry: TimelineEntry, data: TimelineEntryUpdate
) -> TimelineEntry:
    for key, value in data.model_dump(exclude_none=True).items():
        if key == "metadata":
            entry.metadata_ = value
        else:
            setattr(entry, key, value)
    await db.flush()
    return entry


async def delete_entry(db: AsyncSession, entry: TimelineEntry) -> None:
    await db.delete(entry)
    await db.flush()


async def pin_entry(db: AsyncSession, entry: TimelineEntry, pinned: bool) -> TimelineEntry:
    entry.is_pinned = pinned
    await db.flush()
    return entry


def export_csv(entries: list[TimelineEntry]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["occurred_at", "entry_type", "source", "description", "is_pinned", "author_id"],
    )
    writer.writeheader()
    for e in entries:
        writer.writerow({
            "occurred_at": e.occurred_at.isoformat(),
            "entry_type": e.entry_type,
            "source": e.source,
            "description": e.description,
            "is_pinned": e.is_pinned,
            "author_id": str(e.author_id) if e.author_id else "",
        })
    return output.getvalue()
