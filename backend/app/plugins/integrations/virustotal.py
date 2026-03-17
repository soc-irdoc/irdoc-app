"""VirusTotal integration — IOC enrichment for all plan tiers."""
import base64
import logging

import httpx

from app.plugins.registry import register_plugin

logger = logging.getLogger(__name__)

_VT_BASE = "https://www.virustotal.com/api/v3"


@register_plugin
class VirusTotalPlugin:
    name = "virustotal"
    display_name = "VirusTotal"
    category = "ti"
    is_premium = False
    icon = "🦠"
    description = "Enrich IOCs (IP, domain, URL, hash) via VirusTotal."

    config_schema = {
        "api_key": {"type": "password", "label": "API Key", "required": True,
                    "placeholder": "Your VirusTotal API key"},
    }

    async def test_connection(self, config: dict) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"{_VT_BASE}/users/me",
                    headers={"x-apikey": config["api_key"]},
                )
                return r.status_code == 200
        except Exception:
            return False

    async def enrich_ioc(self, ioc: object, config: dict) -> dict:
        ioc_type = getattr(ioc, "ioc_type", "")
        value = getattr(ioc, "value", "")
        endpoint = self._endpoint(ioc_type, value)
        if not endpoint:
            return {}

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.get(endpoint, headers={"x-apikey": config["api_key"]})
                if r.status_code == 404:
                    return {"virustotal": {"found": False}}
                r.raise_for_status()
                data = r.json().get("data", {})
                attrs = data.get("attributes", {})
                stats = attrs.get("last_analysis_stats", {})
                return {
                    "virustotal": {
                        "found": True,
                        "malicious": stats.get("malicious", 0),
                        "suspicious": stats.get("suspicious", 0),
                        "harmless": stats.get("harmless", 0),
                        "undetected": stats.get("undetected", 0),
                        "categories": list(attrs.get("categories", {}).values())[:5],
                        "first_submission": attrs.get("first_submission_date"),
                        "last_analysis_date": attrs.get("last_analysis_date"),
                        "permalink": f"https://www.virustotal.com/gui/{self._vt_type(ioc_type)}/{value}",
                        "reputation": attrs.get("reputation", 0),
                    }
                }
        except Exception as exc:
            logger.warning("VT enrichment failed for %s: %s", value, exc)
            return {}

    def _endpoint(self, ioc_type: str, value: str) -> str | None:
        if ioc_type == "domain":
            return f"{_VT_BASE}/domains/{value}"
        if ioc_type == "ip":
            return f"{_VT_BASE}/ip_addresses/{value}"
        if ioc_type == "url":
            encoded = base64.urlsafe_b64encode(value.encode()).rstrip(b"=").decode()
            return f"{_VT_BASE}/urls/{encoded}"
        if ioc_type == "hash":
            return f"{_VT_BASE}/files/{value}"
        return None

    def _vt_type(self, ioc_type: str) -> str:
        return {"domain": "domain", "ip": "ip-address", "url": "url", "hash": "file"}.get(ioc_type, ioc_type)
