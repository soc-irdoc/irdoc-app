"""
Report service — PDF-only pipeline.
"""
from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.feature_flags import check_feature
from app.models.report import Report
from app.schemas.report import ReportGenerateRequest
from app.services.pdf_template_service import get_template
from app.services.storage.resolver import get_storage_backend
from app.workers.tasks import generate_ai_report, generate_report

logger = logging.getLogger(__name__)


async def enqueue_report(
    db: AsyncSession,
    incident_id: str,
    request: ReportGenerateRequest,
    generated_by: str,
    org_id: str,
) -> Report:
    """Create a pending Report record and enqueue the Celery task."""
    if request.include_ai:
        if not check_feature("ai_summaries"):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="AI summaries require a premium license",
            )

    if request.report_template_id:
        from app.models.template import ReportTemplate
        rt_result = await db.execute(
            select(ReportTemplate).where(
                ReportTemplate.id == request.report_template_id,
            ).where(
                (ReportTemplate.org_id == org_id) | (ReportTemplate.org_id.is_(None))
            )
        )
        if not rt_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Report template not found")
    elif request.pdf_template_id:
        await get_template(request.pdf_template_id, org_id, db)

    report = Report(
        incident_id=incident_id,
        report_template_id=request.report_template_id,
        pdf_template_id=request.pdf_template_id if not request.report_template_id else None,
        report_type="pdf",          # always "pdf" — the format discriminator
        destination=None,
        classification=request.classification,
        generated_by=generated_by,
        is_ai_assisted=request.include_ai,
        status="pending",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    generate_report.delay(str(report.id), request.include_ai)
    return report


async def maybe_trigger_ai_report(db: AsyncSession, incident_id: str, org_id: str) -> None:
    """Fire debounced AI report if enabled. Swallows all errors so callers never break."""
    try:
        from app.services.ai_config_service import get_ai_config
        ai_cfg = await get_ai_config(db, org_id)
        if ai_cfg and ai_cfg.is_enabled:
            await enqueue_ai_report(incident_id=incident_id, org_id=org_id, debounce_seconds=ai_cfg.debounce_seconds)
    except Exception as exc:
        logger.warning("AI auto-trigger failed for %s: %s", incident_id, exc)


async def enqueue_ai_report(incident_id: str, org_id: str, debounce_seconds: int) -> None:
    """
    Debounced auto-trigger: enqueue an AI report generation for an incident.

    Uses Redis to prevent duplicate tasks within the debounce window.
    The debounce key TTL matches the Celery countdown so only one task fires
    per window, but always processes the latest incident state.
    """
    import redis as redis_sync

    from app.core.config import settings

    debounce_key = f"ai_report_debounce:{incident_id}"
    r = redis_sync.from_url(settings.REDIS_URL)
    try:
        is_new = r.set(debounce_key, "1", ex=debounce_seconds, nx=True)
        if is_new:
            generate_ai_report.apply_async(
                kwargs={"incident_id": incident_id, "org_id": org_id},
                countdown=debounce_seconds,
            )
    finally:
        r.close()


async def maybe_trigger_sharepoint_sync(db: AsyncSession, incident_id: str, org_id: str) -> None:
    """Debounced SharePoint sync for non-AI orgs. No-op if AI is enabled (AI path handles push)."""
    try:
        from app.services.ai_config_service import get_ai_config
        from app.services.integration_service import decrypt_config, get_integration
        ai_cfg = await get_ai_config(db, org_id)
        if ai_cfg and ai_cfg.is_enabled:
            return
        sp = await get_integration(org_id, "sharepoint", db)
        if not sp or not sp.is_enabled:
            return
        debounce = int(decrypt_config(sp.config).get("debounce_seconds") or "120")
        import redis as redis_sync

        from app.core.config import settings
        r = redis_sync.from_url(settings.REDIS_URL)
        try:
            r.set(f"sp_nosync:{incident_id}:{org_id}", "1", ex=debounce)
        finally:
            r.close()
    except Exception as exc:
        logger.warning("maybe_trigger_sharepoint_sync failed for %s: %s", incident_id, exc)


async def list_reports(db: AsyncSession, incident_id: str) -> list[Report]:
    result = await db.execute(
        select(Report)
        .where(Report.incident_id == incident_id)
        .order_by(Report.created_at.desc())
    )
    return list(result.scalars().all())


async def get_report(db: AsyncSession, report_id: str) -> Report:
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


async def delete_report(db: AsyncSession, report: Report) -> None:
    if report.storage_path:
        try:
            backend = get_storage_backend()
            await backend.delete(report.storage_path)
        except Exception as exc:
            logger.warning("Failed to delete storage object %s: %s", report.storage_path, exc)
    await db.delete(report)
    await db.commit()
