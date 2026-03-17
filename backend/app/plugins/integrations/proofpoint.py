"""Proofpoint email security integration (premium)."""
import logging
from base64 import b64encode

import httpx

from app.plugins.registry import register_plugin

logger = logging.getLogger(__name__)


@register_plugin
class ProofpointPlugin:
    name = "proofpoint"
    display_name = "Proofpoint"
    category = "email"
    is_premium = True
    icon = "📧"
    description = "Search email messages and traces via Proofpoint TRAP / SIEM API."

    config_schema = {
        "service_url":     {"type": "string",   "label": "Service Principal URL", "required": True,
                            "placeholder": "https://tap-api-v2.proofpoint.com"},
        "principal":       {"type": "string",   "label": "Service Principal",     "required": True},
        "secret":          {"type": "password", "label": "Secret",                "required": True},
    }

    async def test_connection(self, config: dict) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"{config['service_url']}/v2/siem/all",
                    params={"format": "json", "sinceSeconds": 3600},
                    auth=(config["principal"], config["secret"]),
                )
                return r.status_code in (200, 204)
        except Exception:
            return False

    async def search_messages(self, sender: str | None, recipient: str | None,
                               subject: str | None, config: dict) -> list[dict]:
        """Search SIEM events for messages matching given criteria."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    f"{config['service_url']}/v2/siem/messages/delivered",
                    params={"format": "json", "sinceSeconds": 86400 * 7},
                    auth=(config["principal"], config["secret"]),
                )
                r.raise_for_status()
                messages = r.json().get("messagesDelivered", [])
                # Filter client-side (API doesn't support all params)
                results = []
                for msg in messages:
                    if sender and sender.lower() not in str(msg.get("sender", "")).lower():
                        continue
                    if recipient and not any(recipient.lower() in r.lower()
                                             for r in msg.get("recipient", [])):
                        continue
                    if subject and subject.lower() not in str(msg.get("subject", "")).lower():
                        continue
                    results.append(msg)
                return results[:50]
        except Exception as exc:
            logger.warning("Proofpoint search failed: %s", exc)
            return []
