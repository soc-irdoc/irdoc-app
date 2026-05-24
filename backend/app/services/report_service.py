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
from app.workers.tasks import generate_report

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
