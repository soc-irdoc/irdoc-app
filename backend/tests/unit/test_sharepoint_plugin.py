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
    create_resp = _mock_json_response({})
    new_drives = _mock_json_response({"value": [{"id": "drv-new", "name": "IR Reports"}]})
    client = _make_client(
        get_side_effects=[empty_drives, new_drives],
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
async def test_resolve_drive_id_raises_if_creation_fails():
    """Raises ValueError when library creation succeeds but drive still not found."""
    plugin = SharePointPlugin()
    empty_drives = _mock_json_response({"value": []})
    create_resp = _mock_json_response({})
    still_empty = _mock_json_response({"value": []})
    client = _make_client(
        get_side_effects=[empty_drives, still_empty],
        post_return=create_resp,
    )

    with patch("app.plugins.integrations.sharepoint.httpx.AsyncClient", return_value=client):
        with pytest.raises(ValueError, match="could not be created or found"):
            await plugin._resolve_drive_id("site-1", "IR Reports", "tok")
