"""Unit tests for the cached GitHub release version check."""
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services import version_check


def _mock_response(data) -> MagicMock:
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
    client = _make_client(get_return=_mock_response([{"tag_name": "v0.2.0"}]))

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
    client = _make_client(get_return=_mock_response([{"tag_name": "v0.2.0"}]))

    with patch("app.services.version_check.httpx.AsyncClient", return_value=client) as mock_ctor:
        first = await version_check.get_latest_release_version()
        second = await version_check.get_latest_release_version()

    assert first == second == "0.2.0"
    mock_ctor.assert_called_once()


@pytest.mark.asyncio
async def test_prereleases_are_considered():
    # Regression (#67): /releases/latest 404s when every release is a pre-release.
    releases = [
        {"tag_name": "v0.1.2-alpha", "prerelease": True},
        {"tag_name": "v0.1.1-alpha", "prerelease": True},
    ]
    client = _make_client(get_return=_mock_response(releases))

    with patch("app.services.version_check.httpx.AsyncClient", return_value=client):
        latest = await version_check.get_latest_release_version()

    assert latest == "0.1.2-alpha"
    assert client.get.call_args.args[0].endswith("/releases")


def test_pick_latest_uses_version_order_and_skips_drafts():
    releases = [
        {"tag_name": "v0.1.9-alpha"},
        {"tag_name": "v0.2.0", "draft": True},
        {"tag_name": "v0.1.10-alpha"},
        {"tag_name": "not-a-version"},
    ]
    assert version_check.pick_latest(releases) == "0.1.10-alpha"


def test_pick_latest_final_beats_its_prerelease():
    assert version_check.pick_latest([{"tag_name": "v0.2.0-alpha"}, {"tag_name": "v0.2.0"}]) == "0.2.0"


def test_pick_latest_empty():
    assert version_check.pick_latest([]) is None


@pytest.mark.parametrize("latest,current,expected", [
    ("0.1.3-alpha", "0.1.2-alpha", True),
    ("0.1.10-alpha", "0.1.9-alpha", True),
    ("0.1.2", "0.1.2-alpha", True),
    ("0.1.2-alpha", "0.1.2-alpha", False),
    ("0.1.1-alpha", "0.1.2-alpha", False),   # running build is newer than the latest release
    ("0.1.3", "dev", False),                 # unparseable current never nags
    (None, "0.1.2-alpha", False),
])
def test_is_newer(latest, current, expected):
    assert version_check.is_newer(latest, current) is expected
