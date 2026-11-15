"""Evidence register (#150).

Read-only: lists the files an incident has collected (timeline attachments
and incident-level attachments), where each came from, and which hash IOCs
they match. Generated reports are conclusions, not evidence, and are not
attachments, so they never appear here.
"""
import csv
import html
import io
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetTimelineLink
from app.models.attachment import Attachment
from app.models.ioc import IOC, IOCTimelineLink
from app.models.timeline import TimelineEntry
from app.models.user import User
from app.schemas.evidence import (
    EvidenceAssetChip,
    EvidenceFileOut,
    EvidenceIOCMatch,
    EvidenceIOCOut,
    EvidenceSource,
)

# IOC types whose value can be a file hash.
_HASH_IOC_TYPES = ("hash", "file")
_EXCERPT_LEN = 80
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


@dataclass
class EvidenceFilters:
    kind: str | None = None  # "timeline" | "incident"
    mime: str | None = None  # prefix, e.g. "image/" or "application/pdf"
    q: str | None = None  # name or hash substring
    hide_screenshots: bool = False


def excerpt(description: str | None) -> str:
    """Plain-text start of a (possibly rich-text) timeline description."""
    text = _WS_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", description or ""))).strip()
    return text if len(text) <= _EXCERPT_LEN else text[: _EXCERPT_LEN - 1].rstrip() + "…"


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


def _files_query(incident_id: str, filters: EvidenceFilters):
    query = (
        select(Attachment, TimelineEntry)
        .outerjoin(TimelineEntry, Attachment.timeline_entry_id == TimelineEntry.id)
        .where(Attachment.incident_id == incident_id)
    )
    if filters.kind == "timeline":
        query = query.where(Attachment.timeline_entry_id.is_not(None))
    elif filters.kind == "incident":
        query = query.where(Attachment.timeline_entry_id.is_(None))
    if filters.mime:
        query = query.where(Attachment.mime_type.ilike(_escape_like(filters.mime) + "%", escape="\\"))
    if filters.q and filters.q.strip():
        pattern = f"%{_escape_like(filters.q.strip())}%"
        query = query.where(or_(
            Attachment.original_name.ilike(pattern, escape="\\"),
            Attachment.sha256.ilike(pattern, escape="\\"),
        ))
    if filters.hide_screenshots:
        query = query.where(Attachment.is_screenshot.is_(False))
    return query


def _apply_sort(query, sort: str, order: str):
    desc = order == "desc"

    def by(col):
        return col.desc() if desc else col.asc()

    if sort == "uploaded_by":
        query = query.outerjoin(User, Attachment.uploaded_by == User.id)
        keys = [by(func.lower(func.coalesce(User.full_name, User.email)))]
    else:
        column = {
            "name": func.lower(Attachment.original_name),
            # incident-level files before timeline ones
            "kind": case((Attachment.timeline_entry_id.is_(None), 0), else_=1),
            "source": TimelineEntry.occurred_at,
            "type": Attachment.mime_type,
            "size": Attachment.file_size,
            "sha256": Attachment.sha256,
            "screenshot": Attachment.is_screenshot,
        }.get(sort, Attachment.created_at)
        keys = [by(column)]
    return query.order_by(*keys, Attachment.created_at.desc(), Attachment.id)


async def _uploader_names(db: AsyncSession, attachments: list[Attachment]) -> dict[uuid.UUID, str]:
    ids = {a.uploaded_by for a in attachments if a.uploaded_by}
    if not ids:
        return {}
    result = await db.execute(select(User).where(User.id.in_(ids)))
    return {u.id: u.full_name or u.email for u in result.scalars().all()}


async def _asset_chips(db: AsyncSession, entry_ids: set) -> dict[uuid.UUID, list[EvidenceAssetChip]]:
    if not entry_ids:
        return {}
    result = await db.execute(
        select(AssetTimelineLink.timeline_entry_id, Asset)
        .join(Asset, Asset.id == AssetTimelineLink.asset_id)
        .where(AssetTimelineLink.timeline_entry_id.in_(entry_ids))
        .order_by(Asset.name)
    )
    chips: dict[uuid.UUID, list[EvidenceAssetChip]] = defaultdict(list)
    for entry_id, asset in result.all():
        chips[entry_id].append(EvidenceAssetChip(id=asset.id, name=asset.name, asset_type=asset.asset_type))
    return chips


async def _ioc_matches_by_hash(db: AsyncSession, incident_id: str) -> dict[str, list[EvidenceIOCMatch]]:
    result = await db.execute(
        select(IOC).where(IOC.incident_id == incident_id, IOC.ioc_type.in_(_HASH_IOC_TYPES))
    )
    by_hash: dict[str, list[EvidenceIOCMatch]] = defaultdict(list)
    for ioc in result.scalars().all():
        by_hash[ioc.value.strip().lower()].append(
            EvidenceIOCMatch(id=ioc.id, ioc_type=ioc.ioc_type, value=ioc.value)
        )
    return by_hash


async def _linked_iocs(db: AsyncSession, entry_ids: set) -> dict[uuid.UUID, list[EvidenceIOCMatch]]:
    """IOCs linked to each timeline entry (#152)."""
    if not entry_ids:
        return {}
    result = await db.execute(
        select(IOCTimelineLink.timeline_entry_id, IOC)
        .join(IOC, IOC.id == IOCTimelineLink.ioc_id)
        .where(IOCTimelineLink.timeline_entry_id.in_(entry_ids))
        .order_by(IOC.ioc_type, IOC.value)
    )
    by_entry: dict[uuid.UUID, list[EvidenceIOCMatch]] = defaultdict(list)
    for entry_id, ioc in result.all():
        by_entry[entry_id].append(EvidenceIOCMatch(id=ioc.id, ioc_type=ioc.ioc_type, value=ioc.value))
    return by_entry


def _source(entry: TimelineEntry | None) -> EvidenceSource | None:
    if entry is None:
        return None
    return EvidenceSource(
        entry_id=entry.id,
        entry_type=entry.entry_type,
        occurred_at=entry.occurred_at,
        excerpt=excerpt(entry.description),
    )


async def _build_rows(
    db: AsyncSession,
    incident_id: str,
    rows: list[tuple[Attachment, TimelineEntry | None]],
    include_assets: bool,
    include_iocs: bool,
) -> list[EvidenceFileOut]:
    attachments = [a for a, _ in rows]
    names = await _uploader_names(db, attachments)
    chips = (
        await _asset_chips(db, {a.timeline_entry_id for a in attachments if a.timeline_entry_id})
        if include_assets else {}
    )
    matches = await _ioc_matches_by_hash(db, incident_id) if include_iocs else {}
    linked = (
        await _linked_iocs(db, {a.timeline_entry_id for a in attachments if a.timeline_entry_id})
        if include_iocs else {}
    )

    return [
        EvidenceFileOut(
            id=att.id,
            kind="timeline" if att.timeline_entry_id else "incident",
            original_name=att.original_name,
            mime_type=att.mime_type,
            file_size=att.file_size,
            sha256=att.sha256,
            is_screenshot=att.is_screenshot,
            uploaded_by=att.uploaded_by,
            uploaded_by_name=names.get(att.uploaded_by) if att.uploaded_by else None,
            uploaded_at=att.created_at,
            source=_source(entry),
            assets=chips.get(att.timeline_entry_id, []) if include_assets else None,
            ioc_matches=matches.get(att.sha256.lower(), []) if include_iocs else None,
            linked_iocs=linked.get(att.timeline_entry_id, []) if include_iocs else None,
        )
        for att, entry in rows
    ]


async def list_files(
    db: AsyncSession,
    incident_id: str,
    filters: EvidenceFilters,
    sort: str = "uploaded_at",
    order: str = "desc",
    page: int = 1,
    per_page: int = 50,
    include_assets: bool = True,
    include_iocs: bool = True,
) -> tuple[list[EvidenceFileOut], int]:
    query = _files_query(incident_id, filters)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    query = _apply_sort(query, sort, order).offset((page - 1) * per_page).limit(per_page)
    rows = [(a, e) for a, e in (await db.execute(query)).all()]
    return await _build_rows(db, incident_id, rows, include_assets, include_iocs), total


async def all_files(
    db: AsyncSession,
    incident_id: str,
    filters: EvidenceFilters,
    sort: str = "uploaded_at",
    order: str = "desc",
    include_iocs: bool = True,
) -> list[EvidenceFileOut]:
    query = _apply_sort(_files_query(incident_id, filters), sort, order)
    rows = [(a, e) for a, e in (await db.execute(query)).all()]
    return await _build_rows(db, incident_id, rows, include_assets=False, include_iocs=include_iocs)


async def list_iocs(db: AsyncSession, incident_id: str) -> list[EvidenceIOCOut]:
    iocs = list((await db.execute(
        select(IOC).where(IOC.incident_id == incident_id).order_by(IOC.created_at.desc())
    )).scalars().all())
    if not iocs:
        return []

    links = (await db.execute(
        select(IOCTimelineLink.ioc_id, TimelineEntry)
        .join(TimelineEntry, TimelineEntry.id == IOCTimelineLink.timeline_entry_id)
        .where(IOCTimelineLink.ioc_id.in_([i.id for i in iocs]))
        .order_by(TimelineEntry.occurred_at)
    )).all()
    entries_by_ioc: dict[uuid.UUID, list[TimelineEntry]] = defaultdict(list)
    for ioc_id, entry in links:
        entries_by_ioc[ioc_id].append(entry)

    linked_entry_ids = {e.id for entries in entries_by_ioc.values() for e in entries}
    files_per_entry: dict[uuid.UUID, int] = {}
    if linked_entry_ids:
        files_per_entry = dict((await db.execute(
            select(Attachment.timeline_entry_id, func.count())
            .where(Attachment.timeline_entry_id.in_(linked_entry_ids))
            .group_by(Attachment.timeline_entry_id)
        )).all())

    hashes = {i.value.strip().lower() for i in iocs if i.ioc_type in _HASH_IOC_TYPES}
    files_by_hash: dict[str, list[uuid.UUID]] = defaultdict(list)
    if hashes:
        for att_id, sha in (await db.execute(
            select(Attachment.id, Attachment.sha256)
            .where(Attachment.incident_id == incident_id, func.lower(Attachment.sha256).in_(hashes))
        )).all():
            files_by_hash[sha.lower()].append(att_id)

    out = []
    for ioc in iocs:
        entries = entries_by_ioc.get(ioc.id, [])
        is_hash = ioc.ioc_type in _HASH_IOC_TYPES
        out.append(EvidenceIOCOut(
            id=ioc.id,
            ioc_type=ioc.ioc_type,
            value=ioc.value,
            tlp_level=ioc.tlp_level,
            linked_entries=[_source(e) for e in entries],
            file_count=sum(files_per_entry.get(e.id, 0) for e in entries),
            matching_files=files_by_hash.get(ioc.value.strip().lower(), []) if is_hash else [],
        ))
    return out


_CSV_FIELDS = [
    "file_name", "kind", "source_entry_id", "source_entry_type", "source_occurred_at", "source_excerpt",
    "mime_type", "size_bytes", "sha256", "uploaded_by", "uploaded_at", "screenshot", "matching_iocs",
]
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _csv_safe(value) -> str:
    """Neutralise spreadsheet formulas: file names and descriptions are user-controlled."""
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(_FORMULA_PREFIXES) else text


def export_csv(files: list[EvidenceFileOut]) -> str:
    """Chain-of-custody list of the incident's files."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(_CSV_FIELDS)
    for f in files:
        src = f.source
        writer.writerow([_csv_safe(v) for v in (
            f.original_name,
            f.kind,
            src.entry_id if src else "",
            src.entry_type if src else "",
            src.occurred_at.isoformat() if src else "",
            src.excerpt if src else "",
            f.mime_type,
            f.file_size,
            f.sha256,
            f.uploaded_by_name,
            f.uploaded_at.isoformat(),
            "yes" if f.is_screenshot else "no",
            " ".join(m.value for m in (f.ioc_matches or [])),
        )])
    return output.getvalue()
