import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

@pytest.mark.asyncio
async def test_upgrade_welcome_loads_when_mode_upgrade(client):
    from installer.wizard import state
    state.mode = "upgrade"
    state.version_from = "1.1.0"
    state.version_to = "1.2.0"
    resp = await client.get("/upgrade/welcome")
    assert resp.status_code == 200
    assert "1.1.0" in resp.text
    assert "1.2.0" in resp.text


@pytest.mark.asyncio
async def test_upgrade_start_redirects_to_snapshot(client):
    resp = await client.post("/upgrade/start", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "/upgrade/snapshot" in resp.headers["location"]


@pytest.mark.asyncio
async def test_upgrade_snapshot_page_loads(client):
    resp = await client.get("/upgrade/snapshot")
    assert resp.status_code == 200
    assert "Snapshot" in resp.text or "snapshot" in resp.text.lower()


@pytest.mark.asyncio
async def test_upgrade_progress_page_loads(client):
    resp = await client.get("/upgrade/progress")
    assert resp.status_code == 200
    assert "Pull" in resp.text or "upgrade" in resp.text.lower()


@pytest.mark.asyncio
async def test_upgrade_success_page_loads(client):
    from installer.wizard import state
    state.version_from = "1.1.0"
    state.version_to = "1.2.0"
    state.snapshot_dir = "/tmp/fake-snapshot"
    resp = await client.get("/upgrade/success")
    assert resp.status_code == 200
    assert "1.2.0" in resp.text
