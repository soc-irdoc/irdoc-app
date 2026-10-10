"""SharePoint / OneDrive report delivery via Microsoft Graph API."""
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import parse_qs, quote, unquote, urlparse

import httpx

from app.plugins.registry import register_plugin

logger = logging.getLogger(__name__)

_LOGIN_BASE = "https://login.microsoftonline.com"
_GRAPH_BASE = "https://graph.microsoft.com/v1.0"

DEFAULT_FILENAME_PATTERN = "{incident_ref} - {template_name}.pdf"
# Characters SharePoint/OneDrive reject in file names.
_ILLEGAL_FILENAME_CHARS = re.compile(r'["*:<>?/\\|]')


@dataclass(frozen=True)
class SharePointLocation:
    site_url: str        # https://host/sites/Name (or https://host for the root site)
    library: str         # document library, by display name or URL name
    folder: str          # folder inside the library ("" = library root)
    from_url: bool       # library/folder came from a pasted browser URL


def _split(path: str) -> list[str]:
    return [p for p in path.replace("\\", "/").split("/") if p.strip()]


def resolve_location(config: dict) -> SharePointLocation:
    """Work out site, library and folder from the integration config.

    The Site URL field accepts either the plain site URL or any URL copied from
    the browser while viewing a folder (including the ``AllItems.aspx?id=...``
    form and "Copy link" sharing links). When the URL points into a library,
    that location wins over the Document Library / Folder fields. Otherwise
    the Document Library field may itself contain a path ("Documents/General")
    and the Folder field adds to it.
    """
    raw = (config.get("site_url") or "").strip()
    parsed = urlparse(raw)
    segments = _split(unquote(parsed.path))

    # Sharing links: /:f:/r/sites/Name/... or /:b:/s/...
    if segments and segments[0].startswith(":"):
        segments = segments[1:]
        if segments and segments[0] in ("r", "s"):
            segments = segments[1:]

    if len(segments) >= 2 and segments[0].lower() in ("sites", "teams", "personal"):
        site_segments, rest = segments[:2], segments[2:]
    else:
        site_segments, rest = [], segments

    # Library views carry the real folder in ?id= (or the older ?RootFolder=).
    query = parse_qs(parsed.query)
    folder_param = (query.get("id") or query.get("RootFolder") or [None])[0]
    if folder_param:
        rest = _split(folder_param)
        if [p.lower() for p in rest[:len(site_segments)]] == [p.lower() for p in site_segments]:
            rest = rest[len(site_segments):]

    # Drop view pages: .../Forms/AllItems.aspx, .../SitePages/Home.aspx
    for i, part in enumerate(rest):
        if part.lower() == "forms" or part.lower().endswith(".aspx"):
            rest = rest[:i]
            break

    site_url = f"{parsed.scheme}://{parsed.netloc}"
    if site_segments:
        site_url += "/" + "/".join(site_segments)

    if rest:
        return SharePointLocation(site_url, rest[0], "/".join(rest[1:]), from_url=True)

    library_parts = _split(config.get("library") or "IR Reports")
    folder_parts = library_parts[1:] + _split(config.get("folder_path") or "")
    return SharePointLocation(site_url, library_parts[0], "/".join(folder_parts), from_url=False)


def build_report_filename(pattern: str | None, **fields) -> str:
    """Render the Filename Pattern into a SharePoint-safe ``.pdf`` file name.

    Supported placeholders: {incident_ref}, {incident_title}, {template_name},
    {severity}, {status}, {date}, {version}. A pattern with an unknown
    placeholder or a formatting error falls back to the default pattern.
    """
    values = {
        "incident_ref": "INC",
        "incident_title": "Incident",
        "template_name": "Incident Report",
        "severity": "",
        "status": "",
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "version": "",
    }
    values.update({k: v for k, v in fields.items() if v is not None})
    values["incident_title"] = str(values["incident_title"])[:50]

    try:
        name = (pattern or DEFAULT_FILENAME_PATTERN).format(**values)
    except (KeyError, IndexError, ValueError) as exc:
        logger.warning("Invalid SharePoint filename pattern %r (%s); using default", pattern, exc)
        name = DEFAULT_FILENAME_PATTERN.format(**values)

    name = _ILLEGAL_FILENAME_CHARS.sub("-", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    if name.lower().endswith(".pdf"):
        name = name[:-4].rstrip(" .")
    return f"{name[:200] or values['incident_ref']}.pdf"


@register_plugin
class SharePointPlugin:
    name = "sharepoint"
    display_name = "SharePoint / OneDrive"
    category = "storage_sync"
    is_premium = False
    description = "Auto-sync incident reports to SharePoint on every update."

    config_schema = {
        "tenant_id":     {"type": "string",   "label": "Azure Tenant ID",       "required": True},
        "client_id":     {"type": "string",   "label": "App Client ID",         "required": True},
        "client_secret": {"type": "password", "label": "Client Secret",         "required": True},
        "site_url":      {"type": "string",   "label": "SharePoint Site URL",   "required": True,
                          "placeholder": "https://company.sharepoint.com/sites/SOC",
                          "help": "The site URL, or the full browser URL of the target folder "
                                  "(then Document Library and Folder are taken from it)."},
        "library":       {"type": "string",   "label": "Document Library",      "default": "IR Reports",
                          "help": "Library name as shown in SharePoint (e.g. Documents) or as it appears "
                                  "in the URL (e.g. Shared Documents). Created if it doesn't exist."},
        "folder_path":   {"type": "string",   "label": "Folder in Library",
                          "placeholder": "General/Incident Reports",
                          "help": "Optional. Existing folders are reused, missing ones are created."},
        "filename_pattern": {"type": "string", "label": "Filename Pattern",
                             "default": DEFAULT_FILENAME_PATTERN,
                             "placeholder": DEFAULT_FILENAME_PATTERN,
                             "help": "Placeholders: {incident_ref} {incident_title} {template_name} "
                                     "{severity} {status} {date} {version}"},
        "debounce_seconds": {"type": "string", "label": "Sync Delay (seconds)",
                             "default": "600", "placeholder": "600"},
    }

    async def test_connection(self, config: dict) -> bool:
        try:
            location = resolve_location(config)
            token = await self._get_token(config)
            site_id = await self._resolve_site_id(location.site_url, token)
            if location.from_url:
                # A pasted folder URL must point at an existing library.
                await self._resolve_drive_id(site_id, location.library, token, create=False)
            return bool(site_id)
        except Exception:
            return False

    async def push_report(self, report_bytes: bytes, filename: str, config: dict) -> str:
        """Upload bytes to SharePoint into an incident subfolder. Returns webUrl."""
        location = resolve_location(config)
        token = await self._get_token(config)
        site_id = await self._resolve_site_id(location.site_url, token)
        drive_id = await self._resolve_drive_id(
            site_id, location.library, token, create=not location.from_url
        )

        # Graph creates any missing folders on upload and reuses existing ones.
        parts = _split(location.folder)
        if config.get("_incident_ref"):
            parts.append(config["_incident_ref"])
        parts.append(filename)
        upload_path = "/".join(quote(p, safe="") for p in parts)

        upload_url = f"{_GRAPH_BASE}/drives/{drive_id}/root:/{upload_path}:/content"
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
        # Graph wants hostname:/sites/name (or just hostname for the root site)
        parsed = urlparse(site_url)
        path = quote(unquote(parsed.path).strip("/"))
        host = parsed.netloc
        site_ref = f"{host}:/{path}" if path else host
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{_GRAPH_BASE}/sites/{site_ref}",
                headers={"Authorization": f"Bearer {token}"},
            )
            r.raise_for_status()
            return r.json()["id"]

    async def _resolve_drive_id(
        self, site_id: str, library_name: str, token: str, create: bool = True
    ) -> str:
        headers = {"Authorization": f"Bearer {token}"}
        wanted = library_name.strip().casefold()
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{_GRAPH_BASE}/sites/{site_id}/drives",
                headers=headers,
            )
            r.raise_for_status()
            drives = r.json().get("value", [])
            for drive in drives:
                # Match the display name ("Documents", "Documenten") or the
                # name in the URL ("Shared Documents", "Gedeelde documenten"),
                # which differ for the default library and on localised sites.
                url_name = unquote(drive.get("webUrl", "")).rstrip("/").rsplit("/", 1)[-1]
                if wanted in (drive.get("name", "").casefold(), url_name.casefold()):
                    return drive["id"]

            if not create:
                available = ", ".join(d.get("name", "") for d in drives) or "none"
                raise ValueError(
                    f"Document library '{library_name}' not found on the site (available: {available})"
                )

            # Library not found — create it
            r = await client.post(
                f"{_GRAPH_BASE}/sites/{site_id}/lists",
                json={"displayName": library_name, "list": {"template": "documentLibrary"}},
                headers={**headers, "Content-Type": "application/json"},
            )
            r.raise_for_status()

            # Fetch the new library's drive directly by list ID — avoids Graph propagation delay
            created_list_id = r.json()["id"]
            r = await client.get(
                f"{_GRAPH_BASE}/sites/{site_id}/lists/{created_list_id}/drive",
                headers=headers,
            )
            r.raise_for_status()
            return r.json()["id"]
