"""CrowdStrike Falcon integration — detections + host containment (premium)."""
import logging

import httpx

from app.plugins.registry import register_plugin

logger = logging.getLogger(__name__)


@register_plugin
class CrowdStrikePlugin:
    name = "crowdstrike"
    display_name = "CrowdStrike Falcon"
    category = "edr"
    is_premium = True
    icon = "🦅"
    description = "Import detections and contain hosts via CrowdStrike Falcon."

    config_schema = {
        "client_id":     {"type": "string",   "label": "OAuth2 Client ID",     "required": True},
        "client_secret": {"type": "password", "label": "OAuth2 Client Secret", "required": True},
        "base_url":      {"type": "string",   "label": "API Base URL",
                          "default": "https://api.crowdstrike.com",
                          "placeholder": "https://api.crowdstrike.com"},
    }

    async def test_connection(self, config: dict) -> bool:
        try:
            token = await self._get_token(config)
            return bool(token)
        except Exception:
            return False

    async def pull_alerts(self, incident_id: str, config: dict) -> list[dict]:
        """Fetch recent CrowdStrike detections as timeline entry candidates."""
        try:
            token = await self._get_token(config)
            base = config.get("base_url", "https://api.crowdstrike.com")
            async with httpx.AsyncClient(timeout=30) as client:
                # List detection IDs
                r = await client.get(
                    f"{base}/detects/queries/detects/v1",
                    params={"limit": 50, "sort": "created_timestamp.desc"},
                    headers={"Authorization": f"Bearer {token}"},
                )
                r.raise_for_status()
                det_ids = r.json().get("resources", [])[:20]
                if not det_ids:
                    return []

                # Get detection details
                r = await client.post(
                    f"{base}/detects/entities/summaries/GET/v1",
                    json={"ids": det_ids},
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                )
                r.raise_for_status()
                detections = r.json().get("resources", [])
                return [self._det_to_entry(d) for d in detections]
        except Exception as exc:
            logger.warning("CrowdStrike pull_alerts failed: %s", exc)
            return []

    async def contain_host(self, device_id: str, config: dict) -> bool:
        """Initiate network containment on a CrowdStrike-managed host."""
        try:
            token = await self._get_token(config)
            base = config.get("base_url", "https://api.crowdstrike.com")
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.post(
                    f"{base}/devices/entities/devices-actions/v2",
                    params={"action_name": "contain"},
                    json={"ids": [device_id]},
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                )
                r.raise_for_status()
                return True
        except Exception as exc:
            logger.error("CrowdStrike contain failed for %s: %s", device_id, exc)
            return False

    async def _get_token(self, config: dict) -> str:
        base = config.get("base_url", "https://api.crowdstrike.com")
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{base}/oauth2/token",
                data={"client_id": config["client_id"], "client_secret": config["client_secret"]},
            )
            r.raise_for_status()
            return r.json()["access_token"]

    def _det_to_entry(self, d: dict) -> dict:
        return {
            "entry_type": "detection",
            "description": (
                f"[CrowdStrike] {d.get('description', 'Detection')} "
                f"on {d.get('device', {}).get('hostname', 'unknown host')}"
            ),
            "occurred_at": d.get("created_timestamp", ""),
            "source": "crowdstrike",
            "metadata": {
                "cs_detection_id": d.get("detection_id"),
                "severity": d.get("max_severity_displayname"),
                "tactic": d.get("tactic"),
                "technique": d.get("technique"),
                "device_id": d.get("device", {}).get("device_id"),
                "hostname": d.get("device", {}).get("hostname"),
            },
        }
