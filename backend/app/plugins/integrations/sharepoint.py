"""SharePoint / OneDrive report delivery via Microsoft Graph API (premium)."""
import logging

import httpx

from app.plugins.registry import register_plugin

logger = logging.getLogger(__name__)

_LOGIN_BASE = "https://login.microsoftonline.com"
_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


@register_plugin
class SharePointPlugin:
    name = "sharepoint"
    display_name = "SharePoint / OneDrive"
    category = "storage_sync"
    is_premium = True
    icon = "📂"
    description = "Auto-sync incident reports to SharePoint on every update."

    config_schema = {
        "tenant_id":     {"type": "string",   "label": "Azure Tenant ID",       "required": True},
        "client_id":     {"type": "string",   "label": "App Client ID",         "required": True},
        "client_secret": {"type": "password", "label": "Client Secret",         "required": True},
        "site_url":      {"type": "string",   "label": "SharePoint Site URL",   "required": True,
                          "placeholder": "https://company.sharepoint.com/sites/SOC"},
        "library":       {"type": "string",   "label": "Document Library",      "default": "IR Reports"},
        "filename_pattern": {"type": "string", "label": "Filename Pattern",
                             "default": "{incident_ref} - {incident_title}.pdf",
                             "placeholder": "{incident_ref} - {incident_title}.pdf"},
    }

    async def test_connection(self, config: dict) -> bool:
        try:
            token = await self._get_token(config)
            site_id = await self._resolve_site_id(config["site_url"], token)
            return bool(site_id)
        except Exception:
            return False

    async def push_report(self, report_bytes: bytes, filename: str, config: dict) -> str:
        """Upload bytes to SharePoint. Overwrites if file exists. Returns webUrl."""
        token = await self._get_token(config)
        site_id = await self._resolve_site_id(config["site_url"], token)
        drive_id = await self._resolve_drive_id(site_id, config.get("library", "IR Reports"), token)

        upload_url = f"{_GRAPH_BASE}/drives/{drive_id}/root:/{filename}:/content"
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.put(
                upload_url,
                content=report_bytes,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/octet-stream",
                },
            )
            r.raise_for_status()
            return r.json().get("webUrl", "")

    async def _get_token(self, config: dict) -> str:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{_LOGIN_BASE}/{config['tenant_id']}/oauth2/v2.0/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": config["client_id"],
                    "client_secret": config["client_secret"],
                    "scope": "https://graph.microsoft.com/.default",
                },
            )
            r.raise_for_status()
            return r.json()["access_token"]

    async def _resolve_site_id(self, site_url: str, token: str) -> str:
        # site_url like https://company.sharepoint.com/sites/SOC
        # Graph wants hostname:/sites/name
        from urllib.parse import urlparse
        parsed = urlparse(site_url)
        path = parsed.path.lstrip("/")
        host = parsed.netloc
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{_GRAPH_BASE}/sites/{host}:/{path}",
                headers={"Authorization": f"Bearer {token}"},
            )
            r.raise_for_status()
            return r.json()["id"]

    async def _resolve_drive_id(self, site_id: str, library_name: str, token: str) -> str:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{_GRAPH_BASE}/sites/{site_id}/drives",
                headers={"Authorization": f"Bearer {token}"},
            )
            r.raise_for_status()
            drives = r.json().get("value", [])
            for drive in drives:
                if drive.get("name", "").lower() == library_name.lower():
                    return drive["id"]
            # Fallback: default document library
            for drive in drives:
                if drive.get("driveType") == "documentLibrary":
                    return drive["id"]
            raise ValueError(f"Document library '{library_name}' not found in site")
