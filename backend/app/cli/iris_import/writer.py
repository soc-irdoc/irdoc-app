"""Insert one transformed IRIS case into the IRDoc database.

This writes ORM rows directly, like seed_demo.py, rather than going through
the API. The API can't keep the original dates: it has no way to set
opened_at, stamps closed_at with the current time on close, and only issues
current-year references. The checks the API would run are covered instead
by mapping.py's validation (allowed values) and the checks below (unique
reference, case not already imported).

The caller owns the transaction: one case per transaction, committed or
rolled back by __main__.py.
"""
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli.iris_import.transform import EXTERNAL_SOURCE, TIMELINE_SOURCE, CaseBundle, SkipCase
from app.models.asset import Asset, AssetTimelineLink
from app.models.incident import Incident, IncidentExternalRef
from app.models.ioc import IOC, IOCTimelineLink
from app.models.timeline import TimelineEntry
from app.services import audit_service, incident_service

AUDIT_ACTOR = "dfir-iris-import"


@dataclass(frozen=True)
class Actor:
    """The IRDoc user imported incidents are attributed to.

    Plain values, not the ORM User: rolling back a case (dry run, skip,
    failure) expires every loaded object, and reloading one lazily outside
    an awaited query fails under asyncio.
    """
    user_id: uuid.UUID
    org_id: uuid.UUID
    email: str


async def imported_ref(db: AsyncSession, iris_case_id: int) -> str | None:
    """The reference of the incident this IRIS case was imported as, if any."""
    result = await db.execute(
        select(Incident.incident_ref)
        .join(IncidentExternalRef, IncidentExternalRef.incident_id == Incident.id)
        .where(IncidentExternalRef.external_source == EXTERNAL_SOURCE,
               IncidentExternalRef.external_ref == str(iris_case_id))
    )
    return result.scalars().first()


async def check_importable(db: AsyncSession, bundle: CaseBundle) -> None:
    """Raise SkipCase if this case is already in IRDoc or its reference is taken."""
    existing_ref = await imported_ref(db, bundle.iris_case_id)
    if existing_ref:
        raise SkipCase("already_imported", existing_ref)
    if await incident_service.ref_exists(db, bundle.incident.incident_ref):
        raise SkipCase("ref_taken", bundle.incident.incident_ref)


async def write_case(db: AsyncSession, bundle: CaseBundle, user: Actor) -> Incident:
    """Insert the incident and everything in it. Flushes, doesn't commit."""
    await check_importable(db, bundle)
    data = bundle.incident

    incident = Incident(
        id=uuid.uuid4(),
        org_id=user.org_id,
        incident_ref=data.incident_ref,
        title=data.title,
        severity=data.severity,
        status="closed",
        disposition=data.disposition,
        source=data.source,
        assigned_to=user.user_id,
        created_by=user.user_id,
        opened_at=data.opened_at,
        contained_at=None,
        closed_at=data.closed_at,
        executive_summary=data.executive_summary,
        notes=data.notes,
        attack_vector=[],
        affected_users=0,
        metadata_=data.metadata,
        created_at=data.opened_at,
        updated_at=data.closed_at,
    )
    db.add(incident)
    db.add(IncidentExternalRef(
        incident_id=incident.id,
        external_source=EXTERNAL_SOURCE,
        external_ref=data.external_ref,
        external_url=data.external_url,
        created_at=data.opened_at,
    ))
    await db.flush()

    assets_by_iris_id: dict[int, uuid.UUID] = {}
    for a in bundle.assets:
        asset = Asset(
            id=uuid.uuid4(), incident_id=incident.id, asset_type=a.asset_type, name=a.name,
            description=a.description, status=a.status, criticality="medium", tags=a.tags,
            metadata_=a.metadata, added_by=user.user_id, created_at=data.opened_at, updated_at=data.opened_at,
        )
        db.add(asset)
        assets_by_iris_id[a.iris_id] = asset.id

    # An IOC is first seen at the earliest event it's linked to, else when the case opened.
    first_seen: dict[int, object] = {}
    for t in bundle.timeline:
        for iris_ioc in t.ioc_ids:
            first_seen.setdefault(iris_ioc, t.occurred_at)

    iocs_by_iris_id: dict[int, uuid.UUID] = {}
    for i in bundle.iocs:
        seen = min((first_seen[x] for x in i.iris_ids if x in first_seen), default=data.opened_at)
        ioc = IOC(
            id=uuid.uuid4(), incident_id=incident.id, ioc_type=i.ioc_type, value=i.value,
            description=i.description, confidence=50, status="active", first_seen=seen,
            added_by=user.user_id, enrichment={}, tlp_level=i.tlp_level, tags=i.tags, created_at=data.opened_at,
        )
        db.add(ioc)
        for iris_id in i.iris_ids:
            iocs_by_iris_id[iris_id] = ioc.id

    entries: list[tuple[uuid.UUID, list[int], list[int]]] = []
    for t in bundle.timeline:
        entry = TimelineEntry(
            id=uuid.uuid4(), incident_id=incident.id, author_id=user.user_id, entry_type=t.entry_type,
            occurred_at=t.occurred_at, description=t.description, source=TIMELINE_SOURCE,
            is_pinned=False, metadata_=t.metadata, created_at=t.occurred_at, updated_at=t.occurred_at,
        )
        db.add(entry)
        entries.append((entry.id, t.asset_ids, t.ioc_ids))
    await db.flush()

    for entry_id, asset_ids, ioc_ids in entries:
        for asset_id in dict.fromkeys(assets_by_iris_id[a] for a in asset_ids if a in assets_by_iris_id):
            db.add(AssetTimelineLink(asset_id=asset_id, timeline_entry_id=entry_id))
        # Two IRIS IOCs merged into one IRDoc IOC must only be linked once.
        for ioc_id in dict.fromkeys(iocs_by_iris_id[i] for i in ioc_ids if i in iocs_by_iris_id):
            db.add(IOCTimelineLink(ioc_id=ioc_id, timeline_entry_id=entry_id))

    await audit_service.log(
        db,
        org_id=str(user.org_id),
        user_id=str(user.user_id),
        action="incident.imported",
        entity_type="incident",
        entity_id=str(incident.id),
        entity_label=data.incident_ref,
        actor_label=AUDIT_ACTOR,
        diff={
            "source": EXTERNAL_SOURCE,
            "iris_case_id": bundle.iris_case_id,
            "timeline_entries": len(bundle.timeline),
            "assets": len(bundle.assets),
            "iocs": len(bundle.iocs),
            "iocs_not_imported": len(bundle.unsupported_iocs),
        },
    )
    await db.flush()
    return incident
