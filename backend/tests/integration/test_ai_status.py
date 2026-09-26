"""Integration tests for GET /api/v1/ai/status and the AI-disabled guard (#68)."""
import pytest
from httpx import AsyncClient


async def _set_ai(db_session, org, enabled: bool):
    from app.models.ai_config import AiConfig
    db_session.add(AiConfig(org_id=org.id, is_enabled=enabled))
    await db_session.flush()


@pytest.mark.asyncio
async def test_status_disabled_when_unconfigured(client: AsyncClient, auth_headers):
    r = await client.get("/api/v1/ai/status", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["data"] == {"enabled": False}


@pytest.mark.asyncio
async def test_status_enabled(client: AsyncClient, auth_headers, admin_user, db_session):
    await _set_ai(db_session, admin_user[1], True)
    r = await client.get("/api/v1/ai/status", headers=auth_headers)
    assert r.json()["data"] == {"enabled": True}


@pytest.mark.asyncio
async def test_status_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/ai/status")
    assert r.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["summary", "recommendations"])
async def test_generate_rejected_when_ai_disabled(client: AsyncClient, auth_headers, kind):
    inc = await client.post("/api/v1/incidents", json={"title": "X", "severity": "sev2"}, headers=auth_headers)
    r = await client.post(f"/api/v1/incidents/{inc.json()['data']['id']}/ai/{kind}", headers=auth_headers)
    assert r.status_code == 409
    assert "disabled" in r.text
