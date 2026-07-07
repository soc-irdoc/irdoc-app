"""Integration tests for GET /api/v1/version."""
from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_version_returns_current_version(client: AsyncClient, auth_headers):
    with patch("app.api.v1.version.get_latest_release_version", return_value=None):
        resp = await client.get("/api/v1/version", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["version"] == "dev"
    assert data["latest_version"] is None
    assert data["update_available"] is False


@pytest.mark.asyncio
async def test_get_version_flags_update_available(client: AsyncClient, auth_headers):
    with patch("app.api.v1.version.get_latest_release_version", return_value="99.0.0"):
        resp = await client.get("/api/v1/version", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["latest_version"] == "99.0.0"
    assert data["update_available"] is True


@pytest.mark.asyncio
async def test_get_version_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/version")
    assert resp.status_code == 401
