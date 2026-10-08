"""Unit tests for SharePointPlugin."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.plugins.integrations.sharepoint import (
    SharePointPlugin,
    build_report_filename,
    resolve_location,
)


def _mock_json_response(data: dict) -> MagicMock:
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = data
    return r


def _make_client(get_side_effects: list, post_return=None, put_return=None) -> AsyncMock:
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.get = AsyncMock(side_effect=get_side_effects)
    if post_return is not None:
        client.post = AsyncMock(return_value=post_return)
    if put_return is not None:
        client.put = AsyncMock(return_value=put_return)
    return client


@pytest.mark.asyncio
async def test_resolve_drive_id_returns_existing():
    """Returns drive ID when library is already present — no POST called."""
    plugin = SharePointPlugin()
    drives_resp = _mock_json_response({"value": [{"id": "drv-1", "name": "IR Reports"}]})
    client = _make_client(get_side_effects=[drives_resp])

    with patch("app.plugins.integrations.sharepoint.httpx.AsyncClient", return_value=client):
        drive_id = await plugin._resolve_drive_id("site-1", "IR Reports", "tok")

    assert drive_id == "drv-1"
    client.post.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_drive_id_creates_library_when_missing():
    """Creates the document library via Graph when it is not found, then returns the new drive ID."""
    plugin = SharePointPlugin()
    empty_drives = _mock_json_response({"value": []})
    create_resp = _mock_json_response({"id": "list-123"})
    new_drive = _mock_json_response({"id": "drv-new"})
    client = _make_client(
        get_side_effects=[empty_drives, new_drive],
        post_return=create_resp,
    )

    with patch("app.plugins.integrations.sharepoint.httpx.AsyncClient", return_value=client):
        drive_id = await plugin._resolve_drive_id("site-1", "IR Reports", "tok")

    assert drive_id == "drv-new"
    client.post.assert_called_once()
    call_kwargs = client.post.call_args[1]
    assert call_kwargs["json"]["displayName"] == "IR Reports"
    assert call_kwargs["json"]["list"]["template"] == "documentLibrary"


@pytest.mark.asyncio
async def test_resolve_drive_id_raises_on_drive_fetch_failure():
    """Raises HTTPStatusError when fetching the new library's drive fails."""
    import httpx as _httpx

    plugin = SharePointPlugin()
    empty_drives = _mock_json_response({"value": []})
    create_resp = _mock_json_response({"id": "list-123"})

    # Second GET (drive fetch) raises
    failing_drive_resp = MagicMock()
    failing_drive_resp.raise_for_status.side_effect = _httpx.HTTPStatusError(
        "404", request=MagicMock(), response=MagicMock()
    )

    client = _make_client(
        get_side_effects=[empty_drives, failing_drive_resp],
        post_return=create_resp,
    )

    with patch("app.plugins.integrations.sharepoint.httpx.AsyncClient", return_value=client):
        with pytest.raises(_httpx.HTTPStatusError):
            await plugin._resolve_drive_id("site-1", "IR Reports", "tok")


@pytest.mark.asyncio
async def test_push_report_uploads_into_incident_folder():
    """Upload URL includes {incident_ref}/{filename} when _incident_ref is in config."""
    plugin = SharePointPlugin()

    # _get_token: POST → token
    token_client = _make_client(get_side_effects=[], post_return=_mock_json_response({"access_token": "tok"}))
    # _resolve_site_id: GET → site
    site_client = _make_client(get_side_effects=[_mock_json_response({"id": "site-1"})])
    # _resolve_drive_id: GET (found) → no POST needed
    drive_client = _make_client(get_side_effects=[_mock_json_response({"value": [{"id": "drv-1", "name": "IR Reports"}]})])
    # upload PUT
    upload_client = _make_client(
        get_side_effects=[],
        put_return=_mock_json_response({"webUrl": "https://sp.example/INC-2026-0021/report.pdf"}),
    )

    clients = iter([token_client, site_client, drive_client, upload_client])

    config = {
        "tenant_id": "t1", "client_id": "c1", "client_secret": "s1",
        "site_url": "https://company.sharepoint.com/sites/SOC",
        "library": "IR Reports",
        "_incident_ref": "INC-2026-0021",
    }

    with patch("app.plugins.integrations.sharepoint.httpx.AsyncClient", side_effect=clients):
        url = await plugin.push_report(b"pdf", "INC-2026-0021 - Executive Summary.pdf", config)

    assert url == "https://sp.example/INC-2026-0021/report.pdf"
    put_url = upload_client.put.call_args[0][0]
    assert put_url.endswith("/root:/INC-2026-0021/INC-2026-0021%20-%20Executive%20Summary.pdf:/content")


@pytest.mark.asyncio
async def test_push_report_falls_back_to_root_without_incident_ref():
    """Upload URL does NOT include a folder prefix when _incident_ref is absent."""
    plugin = SharePointPlugin()

    token_client = _make_client(get_side_effects=[], post_return=_mock_json_response({"access_token": "tok"}))
    site_client = _make_client(get_side_effects=[_mock_json_response({"id": "site-1"})])
    drive_client = _make_client(get_side_effects=[_mock_json_response({"value": [{"id": "drv-1", "name": "IR Reports"}]})])
    upload_client = _make_client(
        get_side_effects=[],
        put_return=_mock_json_response({"webUrl": "https://sp.example/report.pdf"}),
    )

    clients = iter([token_client, site_client, drive_client, upload_client])

    config = {
        "tenant_id": "t1", "client_id": "c1", "client_secret": "s1",
        "site_url": "https://company.sharepoint.com/sites/SOC",
        "library": "IR Reports",
    }

    with patch("app.plugins.integrations.sharepoint.httpx.AsyncClient", side_effect=clients):
        await plugin.push_report(b"pdf", "report.pdf", config)

    put_url = upload_client.put.call_args[0][0]
    assert put_url.endswith("/root:/report.pdf:/content")


# ── Location resolution (#1.1: reuse existing libraries/folders) ──────────────

_BROWSER_URL = (
    "https://company.sharepoint.com/teams/SecurityOperations_INT/Gedeelde%20documenten/Forms/"
    "AllItems.aspx?id=%2Fteams%2FSecurityOperations%5FINT%2FGedeelde%20documenten%2FGeneral"
    "%2FIncident%20Reports&viewid=3b9d01cb%2D6a99%2D4a20%2D997d%2D6836d70e6425"
    "&newTargetListUrl=%2Fteams%2FSecurityOperations%5FINT%2FGedeelde%20documenten"
)


def test_resolve_location_from_library_view_url():
    loc = resolve_location({"site_url": _BROWSER_URL, "library": "IR Reports"})
    assert loc.site_url == "https://company.sharepoint.com/teams/SecurityOperations_INT"
    assert loc.library == "Gedeelde documenten"
    assert loc.folder == "General/Incident Reports"
    assert loc.from_url is True


def test_resolve_location_from_folder_path_url():
    loc = resolve_location({"site_url": "https://c.sharepoint.com/sites/SOC/Shared%20Documents/IR/2026"})
    assert (loc.site_url, loc.library, loc.folder) == ("https://c.sharepoint.com/sites/SOC", "Shared Documents", "IR/2026")


def test_resolve_location_from_sharing_link():
    loc = resolve_location({"site_url": "https://c.sharepoint.com/:f:/r/sites/SOC/Shared%20Documents/IR?csf=1&e=x"})
    assert (loc.site_url, loc.library, loc.folder) == ("https://c.sharepoint.com/sites/SOC", "Shared Documents", "IR")


def test_resolve_location_from_fields():
    loc = resolve_location({
        "site_url": "https://c.sharepoint.com/sites/SOC/",
        "library": "Documents/General",
        "folder_path": "/Incident Reports/",
    })
    assert (loc.site_url, loc.library, loc.folder) == ("https://c.sharepoint.com/sites/SOC", "Documents", "General/Incident Reports")
    assert loc.from_url is False


def test_resolve_location_defaults_library():
    loc = resolve_location({"site_url": "https://c.sharepoint.com/sites/SOC"})
    assert (loc.library, loc.folder) == ("IR Reports", "")


@pytest.mark.asyncio
async def test_resolve_drive_id_matches_url_name_of_localised_library():
    """'Gedeelde documenten' (URL name) finds the drive whose display name is 'Documenten'."""
    plugin = SharePointPlugin()
    drives = _mock_json_response({"value": [
        {"id": "drv-x", "name": "Other", "webUrl": "https://c.sharepoint.com/teams/T/Other"},
        {"id": "drv-docs", "name": "Documenten", "webUrl": "https://c.sharepoint.com/teams/T/Gedeelde%20documenten"},
    ]})
    client = _make_client(get_side_effects=[drives])

    with patch("app.plugins.integrations.sharepoint.httpx.AsyncClient", return_value=client):
        assert await plugin._resolve_drive_id("site-1", "gedeelde documenten", "tok") == "drv-docs"
    client.post.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_drive_id_without_create_raises_when_missing():
    plugin = SharePointPlugin()
    client = _make_client(get_side_effects=[_mock_json_response({"value": [{"id": "d", "name": "Documents"}]})])

    with patch("app.plugins.integrations.sharepoint.httpx.AsyncClient", return_value=client):
        with pytest.raises(ValueError, match="Documents"):
            await plugin._resolve_drive_id("site-1", "Nope", "tok", create=False)
    client.post.assert_not_called()


@pytest.mark.asyncio
async def test_push_report_uploads_into_existing_folder_from_browser_url():
    plugin = SharePointPlugin()
    token_client = _make_client(get_side_effects=[], post_return=_mock_json_response({"access_token": "tok"}))
    site_client = _make_client(get_side_effects=[_mock_json_response({"id": "site-1"})])
    drive_client = _make_client(get_side_effects=[_mock_json_response({"value": [
        {"id": "drv-docs", "name": "Documenten",
         "webUrl": "https://company.sharepoint.com/teams/SecurityOperations_INT/Gedeelde%20documenten"},
    ]})])
    upload_client = _make_client(get_side_effects=[], put_return=_mock_json_response({"webUrl": "u"}))
    clients = iter([token_client, site_client, drive_client, upload_client])

    config = {
        "tenant_id": "t1", "client_id": "c1", "client_secret": "s1",
        "site_url": _BROWSER_URL, "library": "IR Reports", "_incident_ref": "INC-7",
    }
    with patch("app.plugins.integrations.sharepoint.httpx.AsyncClient", side_effect=clients):
        await plugin.push_report(b"pdf", "INC-7 - Exec.pdf", config)

    site_get = site_client.get.call_args[0][0]
    assert site_get.endswith("/sites/company.sharepoint.com:/teams/SecurityOperations_INT")
    put_url = upload_client.put.call_args[0][0]
    assert "/drives/drv-docs/root:/General/Incident%20Reports/INC-7/INC-7%20-%20Exec.pdf:/content" in put_url


# ── Filename pattern (#1.2) ──────────────────────────────────────────────────

def test_filename_default_pattern():
    assert build_report_filename(None, incident_ref="INC-1", template_name="Executive Summary") == \
        "INC-1 - Executive Summary.pdf"


def test_filename_all_placeholders():
    name = build_report_filename(
        "{date}_{incident_ref}_{severity}_{status}_{template_name}_v{version}_{incident_title}",
        incident_ref="INC-1", template_name="Tech", severity="sev2", status="contained",
        version=3, incident_title="Phish", date="2026-10-08",
    )
    assert name == "2026-10-08_INC-1_sev2_contained_Tech_v3_Phish.pdf"


def test_filename_strips_characters_sharepoint_rejects():
    name = build_report_filename("{incident_title}.pdf", incident_title=r'a/b\c:d*e?"f<g>h|i')
    assert name == "a-b-c-d-e--f-g-h-i.pdf"


def test_filename_unknown_placeholder_falls_back_to_default():
    assert build_report_filename("{customer}.pdf", incident_ref="INC-1", template_name="T") == "INC-1 - T.pdf"


def test_filename_always_ends_in_single_pdf_extension():
    assert build_report_filename("{incident_ref}", incident_ref="INC-1") == "INC-1.pdf"
    assert build_report_filename("{incident_ref}.PDF", incident_ref="INC-1") == "INC-1.pdf"
