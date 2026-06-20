"""
Celery tasks.
Phase 1: verify_file_hash and auto_detect_iocs_from_entry are functional.
Phase 3: generate_report, generate_ai_summary, generate_ai_recommendations — fully implemented.
Phase 4: enrich_ioc, sync_to_sharepoint, send_notification.
"""
import asyncio
import hashlib
import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run an async coroutine from a sync Celery task.

    asyncio.run() creates a fresh event loop, runs the coroutine, and waits for
    all pending callbacks before closing the loop.  The engine pool is disposed
    *inside* the coroutine (while the loop is still active) so asyncpg can
    properly close connections — calling dispose() outside the loop left stale
    connections attached to the old loop, causing the next task to fail with
    "Future attached to a different loop".
    """
    async def _with_pool_cleanup():
        try:
            return await coro
        finally:
            from app.core.database import engine
            await engine.dispose()

    return asyncio.run(_with_pool_cleanup())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def verify_file_hash(self, attachment_id: str):
    """
    Re-verify SHA-256 after storage write.
    Logs and flags any mismatch as a security event.
    """
    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.models.attachment import Attachment
        from app.services.storage.resolver import get_storage_backend
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Attachment).where(Attachment.id == attachment_id))
            attachment = result.scalar_one_or_none()
            if not attachment:
                logger.warning("verify_file_hash: attachment %s not found", attachment_id)
                return

            backend = get_storage_backend()
            try:
                data = await backend.retrieve(attachment.stored_path)
            except FileNotFoundError:
                logger.error("verify_file_hash: file not found in storage: %s", attachment.stored_path)
                return

            computed = hashlib.sha256(data).hexdigest()
            if computed != attachment.sha256:
                logger.critical(
                    "INTEGRITY VIOLATION: attachment %s sha256 mismatch. "
                    "DB=%s computed=%s",
                    attachment_id, attachment.sha256, computed,
                )
            else:
                logger.debug("verify_file_hash: attachment %s OK (%s)", attachment_id, computed[:16])

    run_async(_run())


@celery_app.task(bind=True, max_retries=2)
def auto_detect_iocs_from_entry(self, entry_id: str):
    """
    Scan timeline entry description for IOC patterns.
    Logs detections — surface to UI in a future iteration.
    """
    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.models.timeline import TimelineEntry
        from app.services.ioc_service import auto_detect
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(TimelineEntry).where(TimelineEntry.id == entry_id))
            entry = result.scalar_one_or_none()
            if not entry:
                return

            detected = auto_detect(entry.description)
            if detected:
                logger.info(
                    "auto_detect: entry %s — found %d IOC(s): %s",
                    entry_id,
                    len(detected),
                    [d.value for d in detected[:5]],
                )

    run_async(_run())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_report(self, report_id: str, include_ai: bool = False, org_id: str | None = None, trigger_sharepoint: bool = False):
    async def _run():
        from datetime import datetime, timezone
        from app.core.database import AsyncSessionLocal
        from app.models.report import Report
        from app.models.pdf_template import PdfTemplate
        from app.models.template import ReportTemplate
        from app.models.user import User
        from app.services.report_renderer import render_incident_pdf, render_incident_pdf_from_schema, build_report_payload
        from app.services.graph_service import build_graph
        from app.services.graph_renderer import render_graph_svg
        from app.services.storage.resolver import get_storage_backend
        from sqlalchemy import select, func as sqlfunc

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Report).where(Report.id == report_id))
            report = result.scalar_one_or_none()
            if not report:
                logger.error("generate_report: report %s not found", report_id)
                return

            report.status = "generating"
            await db.commit()

            try:
                user_result = await db.execute(select(User).where(User.id == report.generated_by))
                analyst = user_result.scalar_one_or_none()
                if not analyst:
                    user_result = await db.execute(select(User).where(User.role == "admin").limit(1))
                    analyst = user_result.scalar_one()

                payload = await build_report_payload(
                    incident_id=str(report.incident_id),
                    analyst=analyst,
                    db=db,
                )
                graph_data = await build_graph(str(report.incident_id), db)
                payload.graph_svg = render_graph_svg(graph_data)

                if include_ai:
                    from app.core.feature_flags import check_feature
                    if check_feature("ai_summaries"):
                        from app.services.ai_service import get_ai_provider, build_delta_report_prompt
                        from app.services.ai_config_service import get_ai_config

                        ai_cfg = None
                        if org_id:
                            ai_cfg = await get_ai_config(db, org_id)

                        max_events = ai_cfg.max_timeline_events if ai_cfg else 20

                        # Version scoped to (incident, template) — exclude self to get prior max
                        version_result = await db.execute(
                            select(sqlfunc.max(Report.version_number)).where(
                                Report.incident_id == report.incident_id,
                                Report.report_template_id == report.report_template_id,
                                Report.id != report.id,
                            )
                        )
                        max_ver = version_result.scalar_one_or_none() or 0
                        report.version_number = max_ver + 1

                        # Delta context from previous AI version of same template
                        prev_result = await db.execute(
                            select(Report)
                            .where(
                                Report.incident_id == report.incident_id,
                                Report.report_template_id == report.report_template_id,
                                Report.is_ai_assisted.is_(True),
                                Report.status == "ready",
                                Report.id != report.id,
                            )
                            .order_by(Report.version_number.desc())
                            .limit(1)
                        )
                        prev_report = prev_result.scalar_one_or_none()
                        previous_narrative = prev_report.ai_raw_content if prev_report else None

                        # Audience from template destination (management/analyst/legal/custom)
                        audience = None
                        if report.report_template_id:
                            aud_result = await db.execute(
                                select(ReportTemplate.destination).where(
                                    ReportTemplate.id == report.report_template_id
                                )
                            )
                            audience = aud_result.scalar_one_or_none()

                        provider = get_ai_provider(ai_cfg)
                        sys_p, usr_p = build_delta_report_prompt(
                            payload, previous_narrative, max_events, audience
                        )
                        ai_text = await provider.complete(sys_p, usr_p, 800)
                        payload.ai_executive_summary = ai_text
                        report.ai_raw_content = ai_text

                if report.report_template_id:
                    rt_result = await db.execute(
                        select(ReportTemplate).where(ReportTemplate.id == report.report_template_id)
                    )
                    report_template = rt_result.scalar_one_or_none()
                    if not report_template:
                        raise RuntimeError(f"ReportTemplate {report.report_template_id} not found")

                    schema_json = report_template.schema_json or []
                    brand = {
                        "logo_data_uri": report_template.logo_data_uri,
                        "primary_colour": report_template.primary_colour or "#F97316",
                        "company_name": report_template.company_name,
                    }
                    file_bytes = render_incident_pdf_from_schema(
                        payload=payload,
                        schema_json=schema_json,
                        brand=brand,
                        classification=report.classification.upper(),
                    )
                else:
                    pdf_template = None
                    if report.pdf_template_id:
                        pt_result = await db.execute(
                            select(PdfTemplate).where(PdfTemplate.id == report.pdf_template_id)
                        )
                        pdf_template = pt_result.scalar_one_or_none()

                    file_bytes = render_incident_pdf(
                        payload=payload,
                        pdf_template=pdf_template,
                        classification=report.classification.upper(),
                    )

                backend = get_storage_backend()
                storage_path = f"reports/{report.incident_id}/{report_id}.pdf"
                await backend.store(file_bytes, storage_path)

                report.status = "ready"
                report.storage_path = storage_path
                report.generated_at = datetime.now(timezone.utc)
                await db.commit()

                logger.info(
                    "generate_report: %s completed — %d bytes at %s",
                    report_id, len(file_bytes), storage_path,
                )

                try:
                    _emit_ws(str(report.incident_id), "report:ready", {"report_id": report_id})
                except Exception as ws_err:
                    logger.warning("generate_report: WS emit failed: %s", ws_err)

                if (report.is_ai_assisted or trigger_sharepoint) and org_id:
                    push_report_to_sharepoint.delay(report_id, org_id)

            except Exception as exc:
                logger.exception("generate_report: failed for %s: %s", report_id, exc)
                try:
                    report.status = "failed"
                    report.error_message = str(exc)[:500]
                    await db.commit()
                except Exception:
                    logger.warning("generate_report: could not persist failed status for %s", report_id)
                raise self.retry(exc=exc)

    run_async(_run())


def _emit_ws(incident_id: str, event: str, data: dict):
    """Best-effort Socket.io event emission from worker context via Redis pub/sub."""
    import json
    import redis as redis_sync
    from app.core.config import settings

    r = redis_sync.from_url(settings.REDIS_URL)
    payload = json.dumps({"incident_id": incident_id, "event": event, "data": data})
    r.publish(f"irp:ws:{incident_id}", payload)
    r.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_ai_report(self, incident_id: str, org_id: str):
    """
    Auto-triggered AI report generation routed to the 'ai' queue.

    For each ReportTemplate flagged ai_auto_generate=True in this org:
    - Skips templates with no prior report for this incident (seed not yet generated)
    - Creates one pending Report per activated template and delegates to generate_report
    """
    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.models.report import Report
        from app.models.template import ReportTemplate
        from app.services.ai_config_service import get_ai_config
        from sqlalchemy import select, func as sqlfunc

        async with AsyncSessionLocal() as db:
            ai_cfg = await get_ai_config(db, org_id)
            if not ai_cfg or not ai_cfg.is_enabled:
                return

            tmpl_result = await db.execute(
                select(ReportTemplate).where(
                    ReportTemplate.org_id == org_id,
                    ReportTemplate.ai_auto_generate.is_(True),
                )
            )
            flagged = tmpl_result.scalars().all()
            if not flagged:
                return

            reports_to_generate = []
            for template in flagged:
                count_result = await db.execute(
                    select(sqlfunc.count(Report.id)).where(
                        Report.incident_id == incident_id,
                        Report.report_template_id == template.id,
                    )
                )
                if count_result.scalar_one() == 0:
                    logger.info(
                        "generate_ai_report: skipping template %s for incident %s — no seed report yet",
                        template.id, incident_id,
                    )
                    continue

                report = Report(
                    incident_id=incident_id,
                    report_template_id=template.id,
                    report_type="pdf",
                    classification="confidential",
                    is_ai_assisted=True,
                    status="pending",
                )
                db.add(report)
                reports_to_generate.append(report)

            if not reports_to_generate:
                return

            await db.commit()
            for report in reports_to_generate:
                await db.refresh(report)

        for report in reports_to_generate:
            generate_report.apply_async(
                args=[str(report.id)],
                kwargs={"include_ai": True, "org_id": org_id},
            )

    run_async(_run())


@celery_app.task(bind=True, max_retries=2)
def generate_ai_summary(self, incident_id: str) -> str | None:
    """Generate AI executive summary for an incident (standalone, not tied to a report)."""
    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.core.feature_flags import check_feature
        from app.models.incident import Incident
        from app.models.user import User
        from app.services.report_renderer.payload import build_report_payload
        from app.services.ai_service import get_ai_provider, build_executive_summary_prompt
        from sqlalchemy import select

        if not check_feature("ai_summaries"):
            logger.warning("generate_ai_summary: ai_summaries feature not enabled")
            return None

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Incident).where(Incident.id == incident_id))
            incident = result.scalar_one_or_none()
            if not incident:
                return None

            # Use system user / first admin
            result = await db.execute(select(User).where(User.role == "admin").limit(1))
            analyst = result.scalar_one_or_none()
            if not analyst:
                return None

            payload = await build_report_payload(
                incident_id=incident_id, analyst=analyst, db=db
            )
            provider = get_ai_provider()
            sys_p, usr_p = build_executive_summary_prompt(payload)
            summary = await provider.complete(sys_p, usr_p, 400)
            logger.info("generate_ai_summary: completed for incident %s", incident_id)
            return summary

    return run_async(_run())


@celery_app.task(bind=True, max_retries=2)
def generate_ai_recommendations(self, incident_id: str) -> str | None:
    """Generate AI recommendations for an incident."""
    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.core.feature_flags import check_feature
        from app.models.user import User
        from app.services.report_renderer.payload import build_report_payload
        from app.services.ai_service import get_ai_provider, build_recommendations_prompt
        from sqlalchemy import select

        if not check_feature("ai_summaries"):
            return None

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.role == "admin").limit(1))
            analyst = result.scalar_one_or_none()
            if not analyst:
                return None

            payload = await build_report_payload(
                incident_id=incident_id, analyst=analyst, db=db
            )
            provider = get_ai_provider()
            sys_p, usr_p = build_recommendations_prompt(payload)
            recs = await provider.complete(sys_p, usr_p, 600)
            logger.info("generate_ai_recommendations: completed for incident %s", incident_id)
            return recs

    return run_async(_run())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def enrich_ioc(self, ioc_id: str):
    """
    Multi-provider IOC enrichment (VT, AbuseIPDB, Shodan).
    Runs all enabled TI plugins, merges results, recalculates confidence.
    Emits ioc:enriched WebSocket event on completion.
    """
    async def _run():
        # Ensure all plugins are loaded
        import app.plugins  # noqa: F401 — triggers auto-registration

        from app.core.database import AsyncSessionLocal
        from app.services.enrichment_service import enrich_ioc as do_enrich

        async with AsyncSessionLocal() as db:
            enrichment = await do_enrich(ioc_id, db)
            if enrichment:
                # Reload ioc for confidence value
                from app.models.ioc import IOC
                from sqlalchemy import select
                result = await db.execute(select(IOC).where(IOC.id == ioc_id))
                ioc = result.scalar_one_or_none()
                if ioc:
                    try:
                        _emit_ws(
                            str(ioc.incident_id),
                            "ioc:enriched",
                            {"ioc_id": ioc_id, "enrichment": enrichment, "confidence": ioc.confidence},
                        )
                    except Exception as ws_err:
                        logger.warning("enrich_ioc: WS emit failed: %s", ws_err)

    try:
        run_async(_run())
    except Exception as exc:
        logger.exception("enrich_ioc: failed for %s: %s", ioc_id, exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def sync_to_sharepoint(self, incident_id: str, policy_id: str):
    """
    Debounced SharePoint sync. Renders a PDF report and uploads to SharePoint
    using the policy's linked report template and destination_config credentials.
    """
    async def _run():
        import app.plugins  # noqa: F401 — loads SharePointPlugin

        from app.core.database import AsyncSessionLocal
        from app.models.report import SyncPolicy
        from app.services.report_renderer import render_incident_pdf, build_report_payload
        from app.services.integration_service import decrypt_config
        from app.plugins.registry import PLUGINS
        from sqlalchemy import select
        from datetime import datetime, timezone

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(SyncPolicy).where(SyncPolicy.id == policy_id))
            policy = result.scalar_one_or_none()
            if not policy or not policy.is_active:
                logger.info("sync_to_sharepoint: policy %s inactive or missing", policy_id)
                return

            # Load analyst (admin user for background renders)
            from app.models.user import User
            result = await db.execute(select(User).where(User.role == "admin").limit(1))
            analyst = result.scalar_one_or_none()
            if not analyst:
                return

            payload = await build_report_payload(incident_id=incident_id, analyst=analyst, db=db)
            report_bytes = render_incident_pdf(payload=payload)

            # Build filename from pattern
            pattern = policy.destination_config.get("filename_pattern", "{incident_ref}.pdf")
            try:
                filename = pattern.format(
                    incident_ref=payload.incident.incident_ref,
                    incident_title=payload.incident.title[:50].replace("/", "-"),
                )
            except KeyError:
                filename = f"{payload.incident.incident_ref}.pdf"

            # Decrypt destination config + upload
            config = decrypt_config(dict(policy.destination_config))
            sp_plugin = PLUGINS.get("sharepoint")
            if not sp_plugin:
                raise RuntimeError("SharePoint plugin not loaded")

            sharepoint_url = await sp_plugin().push_report(
                report_bytes, filename, {**config, "_incident_ref": payload.incident.incident_ref}
            )

            policy.last_synced_at = datetime.now(timezone.utc)
            policy.last_sync_status = "success"
            policy.last_error = None
            await db.commit()

            logger.info("sync_to_sharepoint: incident %s → %s", incident_id, sharepoint_url)

            try:
                _emit_ws(incident_id, "sync:complete", {"policy_id": policy_id, "url": sharepoint_url})
            except Exception as ws_err:
                logger.warning("sync_to_sharepoint: WS emit failed: %s", ws_err)

            # Also fire notifications
            send_notification.delay(
                str(analyst.org_id), "sync.complete",
                {"ref": payload.incident.incident_ref, "url": sharepoint_url}
            )

    try:
        run_async(_run())
    except Exception as exc:
        logger.exception("sync_to_sharepoint: failed incident=%s policy=%s: %s", incident_id, policy_id, exc)

        async def _mark_failed():
            from app.core.database import AsyncSessionLocal
            from app.models.report import SyncPolicy
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(SyncPolicy).where(SyncPolicy.id == policy_id))
                policy = result.scalar_one_or_none()
                if policy:
                    policy.last_sync_status = "failed"
                    policy.last_error = str(exc)[:500]
                    await db.commit()
        run_async(_mark_failed())
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2)
def send_notification(self, org_id: str, event: str, payload: dict):
    """
    Send event notification to all enabled comms plugins (Slack, Teams) for the org.
    """
    async def _run():
        import app.plugins  # noqa: F401

        from app.core.database import AsyncSessionLocal
        from app.services.integration_service import get_enabled_plugins_for_org

        async with AsyncSessionLocal() as db:
            plugins = await get_enabled_plugins_for_org(org_id, "comms", db)
            for plugin, config in plugins:
                try:
                    ok = await plugin.send_notification(event, payload, config)
                    logger.debug("send_notification: %s → %s = %s", plugin.name, event, ok)
                except Exception as exc:
                    logger.warning("send_notification: %s failed: %s", plugin.name, exc)

    run_async(_run())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def push_report_to_sharepoint(self, report_id: str, org_id: str):
    """Push an already-generated report PDF to SharePoint and store the returned webUrl."""
    async def _run():
        import app.plugins  # noqa: F401 — loads SharePointPlugin
        from app.core.database import AsyncSessionLocal
        from app.models.report import Report
        from app.models.template import ReportTemplate
        from app.models.incident import Incident
        from app.services.integration_service import get_integration, decrypt_config
        from app.services.storage.resolver import get_storage_backend
        from app.plugins.registry import PLUGINS
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            report = (await db.execute(select(Report).where(Report.id == report_id))).scalar_one_or_none()
            if not report or report.status != "ready" or not report.storage_path:
                logger.info("push_report_to_sharepoint: skipping %s — not ready or no storage_path", report_id)
                return

            sp_record = await get_integration(org_id, "sharepoint", db)
            if not sp_record or not sp_record.is_enabled:
                return

            config = decrypt_config(sp_record.config)
            backend = get_storage_backend()
            file_bytes = await backend.retrieve(report.storage_path)

            template_name = "Incident Report"
            if report.report_template_id:
                tmpl = (await db.execute(
                    select(ReportTemplate).where(ReportTemplate.id == report.report_template_id)
                )).scalar_one_or_none()
                if tmpl:
                    template_name = tmpl.name

            incident = (await db.execute(
                select(Incident).where(Incident.id == report.incident_id)
            )).scalar_one_or_none()

            pattern = config.get("filename_pattern", "{incident_ref} - {template_name}.pdf")
            try:
                filename = pattern.format(
                    incident_ref=incident.incident_ref if incident else "INC",
                    incident_title=(incident.title[:50].replace("/", "-") if incident else "Incident"),
                    template_name=template_name,
                )
            except KeyError:
                filename = f"{(incident.incident_ref if incident else 'INC')} - {template_name}.pdf"

            sp_plugin = PLUGINS.get("sharepoint")
            if not sp_plugin:
                raise RuntimeError("SharePoint plugin not loaded")

            incident_ref = incident.incident_ref if incident else ""
            sharepoint_url = await sp_plugin().push_report(
                file_bytes, filename, {**config, "_incident_ref": incident_ref}
            )

            report.sharepoint_url = sharepoint_url
            await db.commit()

            logger.info("push_report_to_sharepoint: %s → %s", report_id, sharepoint_url)

            try:
                _emit_ws(str(report.incident_id), "report:sharepoint_synced", {
                    "report_id": report_id,
                    "sharepoint_url": sharepoint_url,
                })
            except Exception as ws_err:
                logger.warning("push_report_to_sharepoint: WS emit failed: %s", ws_err)

    try:
        run_async(_run())
    except Exception as exc:
        logger.exception("push_report_to_sharepoint: failed report=%s: %s", report_id, exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2)
def auto_generate_for_sharepoint(self, incident_id: str, org_id: str):
    """
    Non-AI SharePoint sync: regenerate reports for templates already seeded on this incident.

    Only templates for which the user has already manually generated at least one report
    are considered. This mirrors the AI seed-based logic so the user controls which
    templates get auto-synced by generating the first report manually.
    Base scaffold reports (report_template_id=NULL) are excluded.
    """
    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.models.report import Report
        from app.models.template import ReportTemplate
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            # Find distinct custom templates already used for this incident
            seeded_ids_result = await db.execute(
                select(Report.report_template_id)
                .where(
                    Report.incident_id == incident_id,
                    Report.report_template_id.is_not(None),
                )
                .distinct()
            )
            seeded_template_ids = [row[0] for row in seeded_ids_result.all()]

            if not seeded_template_ids:
                logger.info(
                    "auto_generate_for_sharepoint: no seeded templates for incident %s, skipping",
                    incident_id,
                )
                return

            tmpl_result = await db.execute(
                select(ReportTemplate).where(ReportTemplate.id.in_(seeded_template_ids))
            )
            templates = tmpl_result.scalars().all()

            reports_created = []
            for template in templates:
                report = Report(
                    incident_id=incident_id,
                    report_template_id=template.id,
                    report_type="pdf",
                    classification="confidential",
                    is_ai_assisted=False,
                    status="pending",
                )
                db.add(report)
                reports_created.append(report)

            if not reports_created:
                return

            await db.commit()
            for report in reports_created:
                await db.refresh(report)

        for report in reports_created:
            generate_report.apply_async(
                args=[str(report.id)],
                kwargs={"include_ai": False, "org_id": org_id, "trigger_sharepoint": True},
            )

    run_async(_run())


@celery_app.task
def process_expired_sync_locks():
    """
    Beat task: scan for debounce keys that are about to expire and enqueue sync tasks.
    Runs every 10 seconds via Celery Beat.

    Note: With Redis keyspace notifications (notify-keyspace-events Ex) enabled,
    expiry events trigger this via a subscriber. This beat task is a safety net
    for environments where keyspace notifications are not available.
    """
    import redis as redis_sync
    from app.core.config import settings

    r = redis_sync.from_url(settings.REDIS_URL)
    try:
        # Scan for legacy per-policy sync_pending keys
        keys = list(r.scan_iter("sync_pending:*", count=100))
        for key in keys:
            ttl = r.ttl(key)
            # Key expired (TTL = -2) or about to expire (TTL <= 2s) → fire sync
            if ttl == -2 or (0 <= ttl <= 2):
                try:
                    parts = key.decode().split(":")
                    if len(parts) == 3:
                        _, incident_id, policy_id = parts
                        sync_to_sharepoint.delay(incident_id, policy_id)
                        r.delete(key)
                        logger.info("process_expired_sync_locks: fired sync incident=%s policy=%s", incident_id, policy_id)
                except Exception as exc:
                    logger.warning("process_expired_sync_locks: failed to parse key %s: %s", key, exc)

        # Global SharePoint no-AI sync keys: sp_nosync:{incident_id}:{org_id}
        sp_keys = list(r.scan_iter("sp_nosync:*", count=100))
        for key in sp_keys:
            ttl = r.ttl(key)
            if ttl == -2 or (0 <= ttl <= 2):
                try:
                    parts = key.decode().split(":")
                    if len(parts) == 3:
                        _, incident_id, org_id = parts
                        auto_generate_for_sharepoint.delay(incident_id, org_id)
                        r.delete(key)
                        logger.info("process_expired_sync_locks: sp_nosync fired incident=%s org=%s", incident_id, org_id)
                except Exception as exc:
                    logger.warning("process_expired_sync_locks: sp_nosync key %s failed: %s", key, exc)
    finally:
        r.close()


@celery_app.task(bind=True, max_retries=2)
def generate_ai_ioc_narrative(self, ioc_id: str):
    """Generate a plain-English enrichment narrative for an IOC (premium)."""
    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.core.feature_flags import check_feature
        from app.models.ioc import IOC
        from app.services.ai_service import get_ai_provider
        from sqlalchemy import select

        if not check_feature("ai_summaries"):
            return

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(IOC).where(IOC.id == ioc_id))
            ioc = result.scalar_one_or_none()
            if not ioc or not ioc.enrichment:
                return

            system_prompt = (
                "You are a threat intelligence analyst. Summarize enrichment data about an IOC "
                "in 2-3 plain-English sentences suitable for an incident report. Be factual and concise."
            )
            user_prompt = (
                f"IOC Type: {ioc.ioc_type}\nValue: {ioc.value}\n"
                f"Enrichment data: {ioc.enrichment}"
            )

            provider = get_ai_provider()
            narrative = await provider.complete(system_prompt, user_prompt, 200)

            enrichment = dict(ioc.enrichment)
            enrichment["ai_narrative"] = narrative
            ioc.enrichment = enrichment
            await db.commit()

            try:
                _emit_ws(str(ioc.incident_id), "ioc:enriched", {
                    "ioc_id": ioc_id, "enrichment": enrichment, "confidence": ioc.confidence
                })
            except Exception:
                pass

    try:
        run_async(_run())
    except Exception as exc:
        logger.exception("generate_ai_ioc_narrative failed for ioc_id=%s: %s", ioc_id, exc)
        raise self.retry(exc=exc)
