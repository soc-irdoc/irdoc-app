"""Unit tests for the cached GitHub release version check."""
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services import version_check


def _mock_response(data: dict) -> MagicMock:
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = data
    return r


def _make_client(get_return=None, get_side_effect=None) -> AsyncMock:
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    if get_side_effect is not None:
        client.get = AsyncMock(side_effect=get_side_effect)
    else:
        client.get = AsyncMock(return_value=get_return)
    return client


@pytest.fixture(autouse=True)
def reset_cache():
    version_check._cache["value"] = None
    version_check._cache["checked_at"] = float('-inf')
    yield
    version_check._cache["value"] = None
    version_check._cache["checked_at"] = float('-inf')


@pytest.mark.asyncio
async def test_returns_latest_version_on_success():
    client = _make_client(get_return=_mock_response({"tag_name": "v0.2.0"}))

    with patch("app.services.version_check.httpx.AsyncClient", return_value=client):
        latest = await version_check.get_latest_release_version()

    assert latest == "0.2.0"


@pytest.mark.asyncio
async def test_returns_none_when_request_fails():
    client = _make_client(get_side_effect=httpx.ConnectError("boom"))

    with patch("app.services.version_check.httpx.AsyncClient", return_value=client):
        latest = await version_check.get_latest_release_version()

    assert latest is None


@pytest.mark.asyncio
async def test_returns_none_on_404():
    resp = MagicMock()
    resp.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("404", request=MagicMock(), response=MagicMock()))
    client = _make_client(get_return=resp)

    with patch("app.services.version_check.httpx.AsyncClient", return_value=client):
        latest = await version_check.get_latest_release_version()

    assert latest is None


@pytest.mark.asyncio
async def test_caches_result_within_ttl():
    client = _make_client(get_return=_mock_response({"tag_name": "v0.2.0"}))

    with patch("app.services.version_check.httpx.AsyncClient", return_value=client) as mock_ctor:
        first = await version_check.get_latest_release_version()
        second = await version_check.get_latest_release_version()

    assert first == second == "0.2.0"
    mock_ctor.assert_called_once()
