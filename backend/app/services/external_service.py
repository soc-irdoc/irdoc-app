"""
External service: inbound webhook logic.
Normalises external source names, creates incident + optional first entry.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident
from app.schemas.external import ExternalIncidentCreate
from app.schemas.incident import IncidentCreate
from app.services import incident_service, timeline_service
from app.schemas.timeline import TimelineEntryCreate
from datetime import UTC, datetime

SOURCE_DISPLAY: dict[str, str] = {
    "servicedesk_plus": "ServiceDesk Plus",
    "manage_engine": "ManageEngine",
    "jira": "Jira",
    "servicenow": "ServiceNow",
    "pagerduty": "PagerDuty",
    "zendesk": "Zendesk",
}


async def create_from_webhook(
    db: AsyncSession,
    org_id: str,
    payload: ExternalIncidentCreate,
    api_key_id: str | None = None,
) -> Incident:
    incident_data = IncidentCreate(
        title=payload.title,
        severity=payload.severity,
    )

    # Match template by slug if provided
    if payload.template and payload.template != "blank":
        from sqlalchemy import select
        from app.models.template import IncidentTemplate
        result = await db.execute(
            select(IncidentTemplate).where(IncidentTemplate.slug == payload.template)
        )
        template = result.scalar_one_or_none()
        if template:
            incident_data = IncidentCreate(
                title=payload.title,
                severity=payload.severity,
                template_id=str(template.id),
            )

    incident = await incident_service.create_incident(
        db,
        org_id=org_id,
        data=incident_data,
        created_via="api_key",
        created_by_key_id=api_key_id,
    )

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
