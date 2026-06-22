"""Microsoft Sentinel integration — pull alerts, run KQL queries (premium)."""
import logging
from datetime import datetime, timezone

import httpx

from app.plugins.registry import register_plugin

logger = logging.getLogger(__name__)

_MGMT_BASE = "https://management.azure.com"
_LOGIN_BASE = "https://login.microsoftonline.com"


@register_plugin
class SentinelPlugin:
    name = "sentinel"
    display_name = "Microsoft Sentinel"
    category = "siem"
    is_premium = True
    icon = "blue_circle_color.svg"
    description = "Pull alerts and run KQL queries from Microsoft Sentinel."

    config_schema = {
        "tenant_id":     {"type": "string",   "label": "Azure Tenant ID",       "required": True},
        "client_id":     {"type": "string",   "label": "App Client ID",         "required": True},
        "client_secret": {"type": "password", "label": "Client Secret",         "required": True},
        "workspace_id":  {"type": "string",   "label": "Log Analytics Workspace ID", "required": True},
        "subscription_id": {"type": "string", "label": "Subscription ID",       "required": True},
        "resource_group":  {"type": "string", "label": "Resource Group",        "required": True},
        "workspace_name":  {"type": "string", "label": "Sentinel Workspace Name", "required": True},
    }

    async def test_connection(self, config: dict) -> bool:
        try:
            token = await self._get_token(config)
            return bool(token)
        except Exception:
            return False

    async def pull_alerts(self, incident_id: str, config: dict) -> list[dict]:
        """Fetch recent Sentinel incidents/alerts as timeline entry candidates."""
        try:
            token = await self._get_token(config)
            sub = config["subscription_id"]
            rg = config["resource_group"]
            ws = config["workspace_name"]
            url = (
                f"{_MGMT_BASE}/subscriptions/{sub}/resourceGroups/{rg}"
                f"/providers/Microsoft.OperationalInsights/workspaces/{ws}"
                f"/providers/Microsoft.SecurityInsights/incidents"
                f"?api-version=2023-02-01&$top=50"
            )
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url, headers={"Authorization": f"Bearer {token}"})
                r.raise_for_status()
                items = r.json().get("value", [])
                return [self._incident_to_entry(i) for i in items]
        except Exception as exc:
            logger.warning("Sentinel pull_alerts failed: %s", exc)
            return []

    async def run_kql(self, kql: str, config: dict) -> list[dict]:
        """Execute a KQL query against the Log Analytics workspace."""
        try:
            token = await self._get_token(config, resource="https://api.loganalytics.io/")
            ws_id = config["workspace_id"]
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    f"https://api.loganalytics.io/v1/workspaces/{ws_id}/query",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={"query": kql},
                )
                r.raise_for_status()
                result = r.json()
                tables = result.get("tables", [])
                if not tables:
                    return []
                table = tables[0]
                columns = [c["name"] for c in table.get("columns", [])]
                rows = table.get("rows", [])
                return [dict(zip(columns, row)) for row in rows[:200]]
        except Exception as exc:
            logger.warning("Sentinel KQL failed: %s", exc)
            return []

    async def _get_token(self, config: dict, resource: str = "https://management.azure.com/") -> str:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{_LOGIN_BASE}/{config['tenant_id']}/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": config["client_id"],
                    "client_secret": config["client_secret"],
                    "resource": resource,
                },
            )
            r.raise_for_status()
            return r.json()["access_token"]

    def _incident_to_entry(self, item: dict) -> dict:
        props = item.get("properties", {})
        return {
            "entry_type": "detection",
            "description": f"[Sentinel] {props.get('title', 'Alert')} — {props.get('description', '')}",
            "occurred_at": props.get("createdTimeUtc", datetime.now(timezone.utc).isoformat()),
            "source": "sentinel",
            "metadata": {
                "sentinel_incident_id": props.get("incidentNumber"),
                "severity": props.get("severity"),
                "status": props.get("status"),
                "url": item.get("id", ""),
            },
        }
