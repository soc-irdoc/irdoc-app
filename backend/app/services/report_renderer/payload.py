"""
ReportPayload — the data context passed to the Jinja2 rendering engine.

build_report_payload() fetches all incident data from the DB and assembles
the payload. All derived fields (duration, counts, groupings) are computed
here so templates stay logic-free.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.attachment import Attachment
    from app.models.incident import Incident, IncidentExternalRef
    from app.models.ioc import IOC
    from app.models.task import Task
    from app.models.timeline import TimelineEntry
    from app.models.user import User


SEVERITY_LABELS = {
    "sev1": "SEV-1 (Critical)",
    "sev2": "SEV-2 (High)",
    "sev3": "SEV-3 (Medium)",
    "sev4": "SEV-4 (Low)",
}

STATUS_LABELS = {
    "open": "Open",
    "contained": "Contained",
    "closed": "Closed",
    "monitoring": "Monitoring",
}


def _fmt_duration(start: datetime, end: datetime | None) -> str:
    end = end or datetime.now(timezone.utc)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    delta = end - start
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        return "0 minutes"
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes or not hours:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    return " ".join(parts)


@dataclass
class ReportPayload:
    # Raw data
    incident: "Incident"
    entries: list["TimelineEntry"]
    iocs: list["IOC"]
    tasks: list["Task"]
    attachments: list["Attachment"]
    analyst: "User"
    generated_at: datetime

    # Derived fields
    duration_str: str
    entry_count: int
    ioc_count: int
    task_completion_pct: int
    tasks_by_phase: dict[str, list["Task"]]
    entries_by_type: dict[str, list["TimelineEntry"]]
    iocs_by_status: dict[str, list["IOC"]]
    iocs_by_type: dict[str, list["IOC"]]
    severity_label: str
    status_label: str
    external_refs: list["IncidentExternalRef"]
    contained_at_str: str | None
    closed_at_str: str | None

    # AI-generated (populated before rendering if blocks require it)
    ai_executive_summary: str | None = None
    ai_recommendations: str | None = None


def _group_by(items, key_fn) -> dict:
    result: dict = {}
    for item in items:
        k = key_fn(item)
        result.setdefault(k, []).append(item)
    return result


async def build_report_payload(
    incident_id: str,
    analyst: "User",
    db,
) -> ReportPayload:
    from sqlalchemy import select
    from app.models.attachment import Attachment
    from app.models.incident import Incident, IncidentExternalRef
    from app.models.ioc import IOC
    from app.models.task import Task
    from app.models.timeline import TimelineEntry

    # Fetch incident
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one()

    # Fetch external refs
    result = await db.execute(
        select(IncidentExternalRef).where(IncidentExternalRef.incident_id == incident_id)
    )
    external_refs = list(result.scalars().all())

    # Fetch timeline entries (sorted by occurred_at ASC)
    result = await db.execute(
        select(TimelineEntry)
        .where(TimelineEntry.incident_id == incident_id)
        .order_by(TimelineEntry.occurred_at.asc())
    )
    entries = list(result.scalars().all())

    # Fetch IOCs
    result = await db.execute(select(IOC).where(IOC.incident_id == incident_id))
    iocs = list(result.scalars().all())

    # Fetch tasks (sorted by sort_order)
    result = await db.execute(
        select(Task)
        .where(Task.incident_id == incident_id)
        .order_by(Task.sort_order.asc())
    )
    tasks = list(result.scalars().all())

    # Fetch attachments
    result = await db.execute(
        select(Attachment).where(Attachment.incident_id == incident_id)
    )
    attachments = list(result.scalars().all())

    # Compute derived fields
    completed_tasks = [t for t in tasks if t.status == "done"]
    task_completion_pct = (
        round(len(completed_tasks) / len(tasks) * 100) if tasks else 0
    )

    end_time = incident.closed_at or incident.contained_at
    duration_str = _fmt_duration(incident.opened_at, end_time)

    def _fmt_dt(dt: datetime | None) -> str | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M UTC")

    return ReportPayload(
        incident=incident,
        entries=entries,
        iocs=iocs,
        tasks=tasks,
        attachments=attachments,
        analyst=analyst,
        generated_at=datetime.now(timezone.utc),
        duration_str=duration_str,
        entry_count=len(entries),
        ioc_count=len(iocs),
        task_completion_pct=task_completion_pct,
        tasks_by_phase=_group_by(tasks, lambda t: t.phase or "General"),
        entries_by_type=_group_by(entries, lambda e: e.entry_type),
        iocs_by_status=_group_by(iocs, lambda i: i.status),
        iocs_by_type=_group_by(iocs, lambda i: i.ioc_type),
        severity_label=SEVERITY_LABELS.get(incident.severity, incident.severity.upper()),
        status_label=STATUS_LABELS.get(incident.status, incident.status.capitalize()),
        external_refs=external_refs,
        contained_at_str=_fmt_dt(incident.contained_at),
        closed_at_str=_fmt_dt(incident.closed_at),
    )
