"""
IOC service: CRUD + auto-type detection regex.
Same patterns as frontend lib/iocDetector.ts - keep in sync.
"""
import re

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ioc import IOC, IOCTimelineLink
from app.schemas.ioc import IOCCreate, IOCDetected, IOCUpdate

PATTERNS: dict[str, re.Pattern] = {
    "ip": re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
    "email": re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'),
    "sha256": re.compile(r'\b[a-fA-F0-9]{64}\b'),
    "sha1": re.compile(r'\b[a-fA-F0-9]{40}\b'),
    "md5": re.compile(r'\b[a-fA-F0-9]{32}\b'),
    "url": re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+'),
    "domain": re.compile(r'\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b'),
}

# Map sha1/sha256/md5 → hash type
HASH_TYPES = {"sha256", "sha1", "md5"}


def auto_detect(text: str) -> list[IOCDetected]:
    """Scan free text and return suggested IOCs with detected type."""
    found: list[IOCDetected] = []
    seen: set[str] = set()

    # Order matters: emails before domains, URLs before domains, hashes before hex
    for ioc_type in ["url", "email", "sha256", "sha1", "md5", "ip", "domain"]:
        pattern = PATTERNS[ioc_type]
        for match in pattern.finditer(text):
            value = match.group(0).strip()
            if value not in seen:
                seen.add(value)
                # Map hash subtypes to canonical "hash" ioc_type
                display_type = "hash" if ioc_type in HASH_TYPES else ioc_type
                found.append(IOCDetected(ioc_type=display_type, value=value))

    return found


async def create_ioc(
    db: AsyncSession,
    incident_id: str,
    data: IOCCreate,
    added_by: str | None = None,
) -> IOC:
    ioc = IOC(
        incident_id=incident_id,
        ioc_type=data.ioc_type,
        value=data.value,
        description=data.description,
        confidence=data.confidence,
        status=data.status,
        tlp_level=data.tlp_level,
        tags=data.tags,
        added_by=added_by,
    )
    db.add(ioc)
    await db.flush()
    return ioc


async def bulk_import(
    db: AsyncSession,
    incident_id: str,
    text: str,
    added_by: str | None = None,
) -> list[IOC]:
    detected = auto_detect(text)
    iocs = []
    for item in detected:
        ioc = IOC(
            incident_id=incident_id,
            ioc_type=item.ioc_type,
            value=item.value,
            added_by=added_by,
        )
        db.add(ioc)
        iocs.append(ioc)
    await db.flush()
    return iocs


async def list_iocs(db: AsyncSession, incident_id: str) -> list[IOC]:
    result = await db.execute(
        select(IOC).where(IOC.incident_id == incident_id).order_by(IOC.created_at)
    )
    return list(result.scalars().all())


async def get_ioc(db: AsyncSession, ioc_id: str, incident_id: str) -> IOC:
    result = await db.execute(
        select(IOC).where(IOC.id == ioc_id, IOC.incident_id == incident_id)
    )
    ioc = result.scalar_one_or_none()
    if not ioc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="IOC not found")
    return ioc


async def update_ioc(db: AsyncSession, ioc: IOC, data: IOCUpdate) -> IOC:
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(ioc, key, value)
    await db.flush()
    return ioc


async def delete_ioc(db: AsyncSession, ioc: IOC) -> None:
    await db.delete(ioc)
    await db.flush()


async def _entry_in_incident(db: AsyncSession, entry_id: str, incident_id: str):
    from app.models.timeline import TimelineEntry

    entry = (await db.execute(
        select(TimelineEntry).where(TimelineEntry.id == entry_id, TimelineEntry.incident_id == incident_id)
    )).scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timeline entry not found")
    return entry


async def link_to_timeline(db: AsyncSession, incident_id: str, ioc_id: str, entry_id: str):
    """Record that an IOC was seen in a timeline entry of the same incident (#152).

    Returns (ioc, entry, created); linking twice is a no-op (created=False).
    Both must belong to `incident_id`, otherwise 404.
    """
    ioc = await get_ioc(db, ioc_id, incident_id)
    entry = await _entry_in_incident(db, entry_id, incident_id)
    existing = await db.get(IOCTimelineLink, (ioc.id, entry.id))
    if existing is not None:
        return ioc, entry, False
    db.add(IOCTimelineLink(ioc_id=ioc.id, timeline_entry_id=entry.id))
    await db.flush()
    return ioc, entry, True


async def unlink_from_timeline(db: AsyncSession, incident_id: str, ioc_id: str, entry_id: str):
    """Remove a link; returns (ioc, entry, removed)."""
    ioc = await get_ioc(db, ioc_id, incident_id)
    entry = await _entry_in_incident(db, entry_id, incident_id)
    existing = await db.get(IOCTimelineLink, (ioc.id, entry.id))
    if existing is None:
        return ioc, entry, False
    await db.delete(existing)
    await db.flush()
    return ioc, entry, True


async def list_timeline_links(db: AsyncSession, incident_id: str) -> list[IOCTimelineLink]:
    """All IOC-entry links of an incident."""
    result = await db.execute(
        select(IOCTimelineLink)
        .join(IOC, IOC.id == IOCTimelineLink.ioc_id)
        .where(IOC.incident_id == incident_id)
    )
    return list(result.scalars().all())
