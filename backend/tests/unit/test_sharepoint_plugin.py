"""Unit tests for SharePointPlugin."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.plugins.integrations.sharepoint import SharePointPlugin


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
    assert "INC-2026-0021/INC-2026-0021 - Executive Summary.pdf" in put_url


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
