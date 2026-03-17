"""Slack webhook notifications (core — free for all plans)."""
import logging

import httpx

from app.plugins.registry import register_plugin

logger = logging.getLogger(__name__)

_EVENT_MESSAGES = {
    "incident.created":      "🔴 New {severity} incident opened: *{title}* `[{ref}]`",
    "timeline.entry.added":  "📋 {analyst} added *[{entry_type}]* entry to `{ref}`",
    "task.completed":        "✅ Task completed: *{task_title}* — `{ref}`",
    "report.ready":          "📄 *{format}* report ready for `{ref}` — {url}",
    "sync.complete":         "📤 SharePoint updated for `{ref}` — {url}",
    "ioc.added":             "🎯 New IOC added to `{ref}`: *{ioc_type}* `{value}`",
    "incident.closed":       "🟢 Incident closed: *{title}* `[{ref}]`",
    "incident.contained":    "🟡 Incident contained: *{title}* `[{ref}]`",
}


@register_plugin
class SlackPlugin:
    name = "slack"
    display_name = "Slack"
    category = "comms"
    is_premium = False
    icon = "💬"
    description = "Send incident notifications to a Slack channel via incoming webhook."

    config_schema = {
        "webhook_url": {"type": "string", "label": "Incoming Webhook URL", "required": True,
                        "placeholder": "https://hooks.slack.com/services/..."},
        "channel":     {"type": "string", "label": "Channel (optional override)", "required": False,
                        "placeholder": "#security-incidents"},
    }

    async def test_connection(self, config: dict) -> bool:
        try:
            return await self.send_notification("test", {"message": "IRDoc connection test ✓"}, config)
        except Exception:
            return False

    async def send_notification(self, event: str, payload: dict, config: dict) -> bool:
        template = _EVENT_MESSAGES.get(event)
        if template:
            try:
                text = template.format(**payload)
            except KeyError:
                text = f"IRDoc event: `{event}`"
        else:
            text = payload.get("message", f"IRDoc event: `{event}`")

        body: dict = {"text": text}
        if channel := config.get("channel"):
            body["channel"] = channel

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(config["webhook_url"], json=body)
                return r.status_code == 200 and r.text == "ok"
        except Exception as exc:
            logger.warning("Slack notification failed: %s", exc)
            return False
