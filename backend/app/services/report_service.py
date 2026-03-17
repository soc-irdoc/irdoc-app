"""
Report service — full Phase 3 implementation.

Handles report record management; actual generation runs in the Celery worker.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report
from app.models.template import ReportTemplate
from app.schemas.report import ReportGenerateRequest


async def enqueue_report(
    db: AsyncSession,
    incident_id: str,
    request: ReportGenerateRequest,
    generated_by: str,
    org_id: str,
) -> Report:
    """Create a pending Report record and enqueue the Celery task."""
    from app.core.feature_flags import check_feature
    from app.workers.tasks import generate_report

    # Validate format gating
    if request.format in ("pdf",) and not check_feature("report_pdf_export"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="PDF export requires a premium license",
        )
    if request.format == "docx" and not check_feature("report_docx_export"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="DOCX export requires a premium license",
        )
    if request.include_ai and not check_feature("ai_summaries"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="AI summaries require a premium license",
        )

    # Fetch the template to get its destination/name
    result = await db.execute(
        select(ReportTemplate).where(ReportTemplate.id == request.report_template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Report template not found")

    report = Report(
        incident_id=incident_id,
        report_template_id=request.report_template_id,
        report_type=template.name,
        destination=template.destination,
        format=request.format,
        classification=request.classification,
        generated_by=generated_by,
        is_ai_assisted=request.include_ai,
        status="pending",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Fire off Celery task
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
    from app.services.storage.resolver import get_storage_backend
    if report.storage_path:
        try:
            backend = get_storage_backend()
            await backend.delete(report.storage_path)
        except Exception:
            pass  # Best-effort file deletion
    await db.delete(report)
    await db.commit()
