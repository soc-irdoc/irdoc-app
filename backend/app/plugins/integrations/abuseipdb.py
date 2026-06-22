"""AbuseIPDB integration — IP address enrichment."""
import logging

import httpx

from app.plugins.registry import register_plugin

logger = logging.getLogger(__name__)


@register_plugin
class AbuseIPDBPlugin:
    name = "abuseipdb"
    display_name = "AbuseIPDB"
    category = "ti"
    is_premium = False
    icon = "prohibited_color.svg"
    description = "Check IP addresses against the AbuseIPDB threat database."

    config_schema = {
        "api_key": {"type": "password", "label": "API Key", "required": True},
    }

    async def test_connection(self, config: dict) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    "https://api.abuseipdb.com/api/v2/check",
                    params={"ipAddress": "8.8.8.8", "maxAgeInDays": 90},
                    headers={"Key": config["api_key"], "Accept": "application/json"},
                )
                return r.status_code == 200
        except Exception:
            return False

    async def enrich_ioc(self, ioc: object, config: dict) -> dict:
        if getattr(ioc, "ioc_type", "") != "ip":
            return {}
        value = getattr(ioc, "value", "")
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(
                    "https://api.abuseipdb.com/api/v2/check",
                    params={"ipAddress": value, "maxAgeInDays": 90, "verbose": ""},
                    headers={"Key": config["api_key"], "Accept": "application/json"},
                )
                r.raise_for_status()
                d = r.json().get("data", {})
                return {
                    "abuseipdb": {
                        "abuse_confidence_score": d.get("abuseConfidenceScore", 0),
                        "country_code": d.get("countryCode"),
                        "isp": d.get("isp"),
                        "domain": d.get("domain"),
                        "total_reports": d.get("totalReports", 0),
                        "num_distinct_users": d.get("numDistinctUsers", 0),
                        "last_reported_at": d.get("lastReportedAt"),
                        "is_public": d.get("isPublic", True),
                        "usage_type": d.get("usageType"),
                    }
                }
        except Exception as exc:
            logger.warning("AbuseIPDB enrichment failed for %s: %s", value, exc)
            return {}
