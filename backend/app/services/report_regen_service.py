"""
Automatic report regeneration after incident changes.

Once an analyst has generated a report for an incident, every later change to
that incident produces a new version of each report "seed" (template, or the
base report) already generated for it. This happens regardless of which
integrations are enabled — AI and SharePoint only change *how* a version is
produced:

  - AI enabled, licensed, and the template flagged ai_auto_generate
      → the new version includes an AI narrative
  - SharePoint integration enabled
      → the new version is pushed to the document library once rendered

Debounce is trailing-edge: every change stores a fresh token in Redis and
schedules auto_regenerate_reports with a countdown. When a run fires it only
proceeds if its token is still the latest, so a burst of edits yields one
regeneration reflecting the final state.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.feature_flags import check_feature
from app.models.report import Report
from app.models.template import ReportTemplate

logger = logging.getLogger(__name__)

DEFAULT_DEBOUNCE_SECONDS = 60
SHAREPOINT_DEFAULT_DEBOUNCE_SECONDS = 120
# The token must outlive the countdown, otherwise the scheduled run would find
# no token and skip itself.
_TOKEN_TTL_MARGIN_SECONDS = 300


@dataclass(frozen=True)
class RegenJob:
    report_id: str
    include_ai: bool
    trigger_sharepoint: bool


def regen_token_key(incident_id: str) -> str:
    return f"report_regen:{incident_id}"


def _redis_client():
    import redis as redis_sync

    from app.core.config import settings

    return redis_sync.from_url(settings.REDIS_URL)


def is_latest_token(r, incident_id: str, token: str) -> bool:
    current = r.get(regen_token_key(incident_id))
    return current is not None and current.decode() == token


async def _ai_enabled(db: AsyncSession, org_id: str):
    from app.services.ai_config_service import get_ai_config

    ai_cfg = await get_ai_config(db, org_id)
    return ai_cfg if ai_cfg and ai_cfg.is_enabled else None


async def _sharepoint_enabled(db: AsyncSession, org_id: str):
    from app.services.integration_service import get_integration

    sp = await get_integration(org_id, "sharepoint", db)
    return sp if sp and sp.is_enabled else None


async def resolve_debounce_seconds(db: AsyncSession, org_id: str) -> int:
    ai_cfg = await _ai_enabled(db, org_id)
    if ai_cfg:
        return ai_cfg.debounce_seconds
    sp = await _sharepoint_enabled(db, org_id)
    if sp:
        from app.services.integration_service import decrypt_config

        raw = decrypt_config(sp.config).get("debounce_seconds")
        try:
            return int(raw) if raw else SHAREPOINT_DEFAULT_DEBOUNCE_SECONDS
        except (TypeError, ValueError):
            return SHAREPOINT_DEFAULT_DEBOUNCE_SECONDS
    return DEFAULT_DEBOUNCE_SECONDS


async def maybe_trigger_report_regen(db: AsyncSession, incident_id: str, org_id: str) -> None:
    """Schedule a debounced regeneration. Swallows all errors so callers never break."""
    try:
        from app.workers.tasks import auto_regenerate_reports

        debounce = await resolve_debounce_seconds(db, org_id)
        token = uuid.uuid4().hex
        r = _redis_client()
        try:
            r.set(regen_token_key(incident_id), token, ex=debounce + _TOKEN_TTL_MARGIN_SECONDS)
        finally:
            r.close()
        auto_regenerate_reports.apply_async(args=[incident_id, org_id, token], countdown=debounce)
    except Exception as exc:
        logger.warning("Report regeneration trigger failed for %s: %s", incident_id, exc)


async def next_version_number(
    db: AsyncSession, incident_id, report_template_id
) -> int:
    """Next version for an (incident, template) seed; base reports have their own sequence."""
    template_filter = (
        Report.report_template_id.is_(None)
        if report_template_id is None
        else Report.report_template_id == report_template_id
    )
    result = await db.execute(
        select(func.max(Report.version_number)).where(
            Report.incident_id == incident_id, template_filter
        )
    )
    return (result.scalar_one_or_none() or 0) + 1


async def create_regeneration_reports(
    db: AsyncSession, incident_id: str, org_id: str
) -> list[RegenJob]:
    """Create one pending Report per seed already generated for the incident."""
    latest_per_seed: dict[object, Report] = {}
    result = await db.execute(
        select(Report)
        .where(Report.incident_id == incident_id)
        .order_by(Report.created_at, Report.version_number)
    )
    for report in result.scalars().all():
        latest_per_seed[report.report_template_id] = report

    if not latest_per_seed:
        return []

    ai_active = bool(await _ai_enabled(db, org_id)) and check_feature("ai_summaries")
    trigger_sharepoint = bool(await _sharepoint_enabled(db, org_id))

    template_ids = [tid for tid in latest_per_seed if tid is not None]
    flagged: set = set()
    if template_ids:
        tmpl_result = await db.execute(
            select(ReportTemplate.id).where(
                ReportTemplate.id.in_(template_ids),
                ReportTemplate.ai_auto_generate.is_(True),
            )
        )
        flagged = set(tmpl_result.scalars().all())

    created: list[tuple[Report, bool]] = []
    for template_id, previous in latest_per_seed.items():
        include_ai = ai_active and template_id in flagged
        report = Report(
            incident_id=previous.incident_id,
            report_template_id=template_id,
            pdf_template_id=previous.pdf_template_id if template_id is None else None,
            report_type="pdf",
            classification=previous.classification,
            generated_by=previous.generated_by,
            is_ai_assisted=include_ai,
            version_number=await next_version_number(db, previous.incident_id, template_id),
            status="pending",
        )
        db.add(report)
        created.append((report, include_ai))

    await db.commit()
    return [
        RegenJob(report_id=str(report.id), include_ai=include_ai, trigger_sharepoint=trigger_sharepoint)
        for report, include_ai in created
    ]
