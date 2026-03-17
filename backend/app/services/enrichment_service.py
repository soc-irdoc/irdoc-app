"""
IOC enrichment service — multi-provider enrichment + confidence score recalculation.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ioc import IOC
from app.models.incident import Incident
from app.services.integration_service import get_enabled_plugins_for_org

logger = logging.getLogger(__name__)


def calculate_confidence(enrichment: dict) -> int:
    """
    Compute a confidence score (0–100) from enrichment data.
    Weighted average: VT (60%) + AbuseIPDB (40%) when available.
    """
    scores: list[tuple[float, float]] = []

    if vt := enrichment.get("virustotal"):
        total = sum([
            vt.get("malicious", 0),
            vt.get("suspicious", 0),
            vt.get("harmless", 0),
            vt.get("undetected", 0),
        ])
        if total > 0:
            raw = (vt["malicious"] + vt.get("suspicious", 0) * 0.5) / total * 100
            scores.append((raw, 0.6))

    if ab := enrichment.get("abuseipdb"):
        scores.append((float(ab.get("abuse_confidence_score", 0)), 0.4))

    if not scores:
        return 50  # Unknown — no enrichment data

    total_weight = sum(w for _, w in scores)
    weighted = sum(s * w for s, w in scores) / total_weight
    return max(0, min(100, round(weighted)))


async def enrich_ioc(ioc_id: str, db: AsyncSession) -> dict:
    """
    Run all enabled TI plugins against the IOC, merge results into enrichment JSONB,
    recalculate confidence, and update the IOC row.
    Returns the updated enrichment dict.
    """
    result = await db.execute(select(IOC).where(IOC.id == ioc_id))
    ioc = result.scalar_one_or_none()
    if not ioc:
        logger.warning("enrich_ioc: IOC %s not found", ioc_id)
        return {}

    # Resolve org_id via the incident
    result = await db.execute(select(Incident).where(Incident.id == ioc.incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        return {}

    org_id = str(incident.org_id)
    plugins = await get_enabled_plugins_for_org(org_id, "ti", db)

    if not plugins:
        logger.debug("enrich_ioc: no TI plugins enabled for org %s", org_id)
        return ioc.enrichment or {}

    merged: dict = dict(ioc.enrichment or {})

    for plugin, config in plugins:
        try:
            result_data = await plugin.enrich_ioc(ioc, config)
            if result_data:
                merged.update(result_data)
                logger.debug("enrich_ioc: %s enriched %s (%s)", plugin.name, ioc_id, ioc.ioc_type)
        except Exception as exc:
            logger.warning("enrich_ioc: plugin %s failed for %s: %s", plugin.name, ioc_id, exc)

    # Add last_enriched timestamp
    merged["_enriched_at"] = datetime.now(timezone.utc).isoformat()

    # Recalculate confidence
    new_confidence = calculate_confidence(merged)

    ioc.enrichment = merged
    ioc.confidence = new_confidence
    await db.commit()

    logger.info(
        "enrich_ioc: %s (%s=%s) enriched by %d plugins → confidence=%d",
        ioc_id, ioc.ioc_type, ioc.value[:40], len(plugins), new_confidence,
    )
    return merged


async def trigger_enrichment_for_new_ioc(ioc_id: str, org_id: str, db: AsyncSession) -> bool:
    """
    Called by the IOC creation API route. Enqueues the Celery enrichment task
    only if at least one TI plugin is enabled for the org.
    """
    plugins = await get_enabled_plugins_for_org(org_id, "ti", db)
    if not plugins:
        return False

    from app.workers.tasks import enrich_ioc as enrich_task
    enrich_task.delay(ioc_id)
    return True
