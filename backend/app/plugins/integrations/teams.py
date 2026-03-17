"""Microsoft Teams webhook notifications (core — free for all plans)."""
import logging

import httpx

from app.plugins.registry import register_plugin

logger = logging.getLogger(__name__)

_SEVERITY_COLORS = {
    "sev1": "FF0000",
    "sev2": "FF8C00",
    "sev3": "FFD700",
    "sev4": "36A64F",
}


@register_plugin
class TeamsPlugin:
    name = "teams"
    display_name = "Microsoft Teams"
    category = "comms"
    is_premium = False
    icon = "🟣"
    description = "Send incident notifications to a Microsoft Teams channel via webhook."

    config_schema = {
        "webhook_url": {"type": "string", "label": "Incoming Webhook URL", "required": True,
                        "placeholder": "https://outlook.office.com/webhook/..."},
    }

    async def test_connection(self, config: dict) -> bool:
        try:
            return await self.send_notification("test", {"message": "IRDoc connection test ✓"}, config)
        except Exception:
            return False

    async def send_notification(self, event: str, payload: dict, config: dict) -> bool:
        title, text = self._format_event(event, payload)
        body = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": _SEVERITY_COLORS.get(payload.get("severity", ""), "0078D4"),
            "summary": title,
            "sections": [{"activityTitle": title, "activityText": text}],
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(config["webhook_url"], json=body)
                return r.status_code in (200, 202)
        except Exception as exc:
            logger.warning("Teams notification failed: %s", exc)
            return False

    def _format_event(self, event: str, payload: dict) -> tuple[str, str]:
        ref = payload.get("ref", "")
        title_map = {
            "incident.created":     f"🔴 New Incident: {payload.get('title', ref)}",
            "timeline.entry.added": f"📋 Timeline update: {ref}",
            "task.completed":       f"✅ Task completed: {ref}",
            "report.ready":         f"📄 Report ready: {ref}",
            "sync.complete":        f"📤 SharePoint sync complete: {ref}",
            "ioc.added":            f"🎯 New IOC: {ref}",
            "incident.closed":      f"🟢 Incident closed: {ref}",
        }
        title = title_map.get(event, f"IRDoc: {event}")
        text = payload.get("message", str(payload))
        return title, text
