"""Shodan integration — IP and domain enrichment."""
import logging

import httpx

from app.plugins.registry import register_plugin

logger = logging.getLogger(__name__)


@register_plugin
class ShodanPlugin:
    name = "shodan"
    display_name = "Shodan"
    category = "ti"
    is_premium = False
    icon = "satellite_antenna_color.svg"
    description = "Enrich IP addresses and domains with Shodan port/host data."

    config_schema = {
        "api_key": {"type": "password", "label": "API Key", "required": True},
    }

    async def test_connection(self, config: dict) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    "https://api.shodan.io/api-info",
                    params={"key": config["api_key"]},
                )
                return r.status_code == 200
        except Exception:
            return False

    async def enrich_ioc(self, ioc: object, config: dict) -> dict:
        ioc_type = getattr(ioc, "ioc_type", "")
        value = getattr(ioc, "value", "")
        if ioc_type not in ("ip", "domain"):
            return {}
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                if ioc_type == "ip":
                    r = await client.get(
                        f"https://api.shodan.io/shodan/host/{value}",
                        params={"key": config["api_key"]},
                    )
                else:
                    r = await client.get(
                        "https://api.shodan.io/dns/resolve",
                        params={"hostnames": value, "key": config["api_key"]},
                    )
                    if r.status_code == 200:
                        ip = r.json().get(value)
                        if ip:
                            r = await client.get(
                                f"https://api.shodan.io/shodan/host/{ip}",
                                params={"key": config["api_key"]},
                            )
                        else:
                            return {}
                    else:
                        return {}

                if r.status_code == 404:
                    return {"shodan": {"found": False}}
                r.raise_for_status()
                data = r.json()
                return {
                    "shodan": {
                        "found": True,
                        "ports": data.get("ports", [])[:20],
                        "hostnames": data.get("hostnames", [])[:10],
                        "country": data.get("country_name"),
                        "country_code": data.get("country_code"),
                        "org": data.get("org"),
                        "isp": data.get("isp"),
                        "asn": data.get("asn"),
                        "os": data.get("os"),
                        "last_update": data.get("last_update"),
                        "vulns": list(data.get("vulns", {}).keys())[:10],
                    }
                }
        except Exception as exc:
            logger.warning("Shodan enrichment failed for %s: %s", value, exc)
            return {}
