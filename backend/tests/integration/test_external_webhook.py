"""Integration tests for inbound webhook endpoint."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.api_key import APIKey
from app.core.security import generate_api_key


@pytest.fixture
async def api_key_headers(db_session: AsyncSession, admin_user):
    user, org = admin_user
    raw_key, key_prefix, key_hash = generate_api_key()
    api_key = APIKey(
        org_id=org.id,
        created_by=user.id,
        name="Test Webhook Key",
        key_prefix=key_prefix,
        key_hash=key_hash,
        scopes=["incidents:create"],
    )
    db_session.add(api_key)
    await db_session.flush()
    return {"Authorization": f"ApiKey {raw_key}"}


@pytest.mark.asyncio
async def test_create_incident_via_webhook(client: AsyncClient, api_key_headers):
    response = await client.post(
        "/api/v1/external/incidents",
        json={
            "title": "SDP Ticket #4421 — Suspicious Login",
            "severity": "sev2",
            "external_ref": "SDP-2026-4421",
            "external_source": "servicedesk_plus",
            "external_url": "https://sdp.example.com/requests/4421",
            "description": "User reported inability to log in after suspicious activity.",
            "reported_by": "user@company.com",
        },
        headers=api_key_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["incident_ref"].startswith("INC-")
    assert data["external_ref"] == "SDP-2026-4421"
    assert "workspace_url" in data


@pytest.mark.asyncio
async def test_webhook_requires_api_key(client: AsyncClient):
    response = await client.post(
        "/api/v1/external/incidents",
        json={"title": "No auth", "severity": "sev2"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_webhook_wrong_scope(client: AsyncClient, admin_user, db_session: AsyncSession):
    _, org = admin_user
    user, _ = admin_user
    raw_key, key_prefix, key_hash = generate_api_key()
    api_key = APIKey(
        org_id=org.id,
        created_by=user.id,
        name="Read-only key",
        key_prefix=key_prefix,
        key_hash=key_hash,
        scopes=["incidents:read"],  # Wrong scope
    )
    db_session.add(api_key)
    await db_session.flush()

    response = await client.post(
        "/api/v1/external/incidents",
        json={"title": "Should fail", "severity": "sev2"},
        headers={"Authorization": f"ApiKey {raw_key}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_webhook_invalid_severity(client: AsyncClient, api_key_headers):
    response = await client.post(
        "/api/v1/external/incidents",
        json={"title": "Bad severity", "severity": "critical"},  # invalid
        headers=api_key_headers,
    )
    assert response.status_code == 422
