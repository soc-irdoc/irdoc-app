"""
External service: inbound webhook logic.
Normalises external source names, creates incident + optional first entry.
"""
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident
from app.schemas.external import ExternalIncidentCreate
from app.schemas.incident import IncidentCreate
from app.schemas.timeline import TimelineEntryCreate
from app.services import incident_service, timeline_service

SOURCE_DISPLAY: dict[str, str] = {
    "servicedesk_plus": "ServiceDesk Plus",
    "manage_engine": "ManageEngine",
    "jira": "Jira",
    "servicenow": "ServiceNow",
    "pagerduty": "PagerDuty",
    "zendesk": "Zendesk",
}


def _raise_ref_taken(incident_ref: str, existing: Incident | None) -> None:
    """409 for a caller-chosen number already in use. `existing` is passed only
    when it is in the caller's org - never reveal another org's incident."""
    detail: dict = {"message": f"Incident {incident_ref} already exists", "incident_ref": incident_ref}
    if existing is not None:
        detail["incident_id"] = str(existing.id)
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


async def create_from_webhook(
    db: AsyncSession,
    org_id: str,
    payload: ExternalIncidentCreate,
    api_key_id: str | None = None,
) -> Incident:
    incident_data = IncidentCreate(
        title=payload.title,
        severity=payload.severity,
        source=payload.source,
    )

    # Match template by slug if provided: only the caller's org's templates and
    # the system ones, never hidden ones. An unknown slug is an error rather
    # than a silently blank incident (#168).
    if payload.template and payload.template != "blank":
        from sqlalchemy import select

        from app.models.template import IncidentTemplate
        result = await db.execute(
            select(IncidentTemplate)
            .where(
                IncidentTemplate.slug == payload.template,
                (IncidentTemplate.org_id == org_id) | (IncidentTemplate.org_id == None),  # noqa: E711
                IncidentTemplate.is_hidden == False,  # noqa: E712
            )
            # The org's own template wins over a system one with the same slug
            # (possible only for rows created before migration 031).
            .order_by(IncidentTemplate.org_id.is_(None))
            .limit(1)
        )
        template = result.scalar_one_or_none()
        if template is None:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown template '{payload.template}'",
            )
        incident_data = IncidentCreate(
            title=payload.title,
            severity=payload.severity,
            source=payload.source,
            template_id=str(template.id),
        )

    incident_ref = None
    if payload.incident_number:
        year = datetime.now(UTC).year
        incident_ref = incident_service.format_ref(year, int(payload.incident_number))
        existing = await incident_service.ref_exists(db, incident_ref)
        if existing:
            _raise_ref_taken(incident_ref, existing if str(existing.org_id) == str(org_id) else None)

    try:
        incident = await incident_service.create_incident(
            db,
            org_id=org_id,
            data=incident_data,
            created_via="api_key",
            created_by_key_id=api_key_id,
            incident_ref=incident_ref,
        )
    except IntegrityError:
        # Lost a race with a concurrent request for the same number.
        if incident_ref is None:
            raise
        await db.rollback()
        _raise_ref_taken(incident_ref, None)

    # Store external ref
    if payload.external_ref and payload.external_source:
        await incident_service.add_external_ref(
            db,
            incident_id=str(incident.id),
            external_source=payload.external_source,
            external_ref=payload.external_ref,
            external_url=payload.external_url,
        )

    # Create first timeline entry from description
    if payload.description:
        source_display = SOURCE_DISPLAY.get(payload.external_source or "", payload.external_source or "external")
        entry_data = TimelineEntryCreate(
            entry_type="note",
            occurred_at=datetime.now(UTC),
            description=payload.description,
            source=source_display,
        )
        await timeline_service.create_entry(db, str(incident.id), entry_data)

    return incident
