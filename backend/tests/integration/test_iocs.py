"""Integration tests for IOC endpoints."""
import pytest
from httpx import AsyncClient


@pytest.fixture
async def incident_id(client: AsyncClient, auth_headers):
    r = await client.post(
        "/api/v1/incidents",
        json={"title": "IOC Test Incident", "severity": "sev1"},
        headers=auth_headers,
    )
    return r.json()["data"]["id"]


@pytest.mark.asyncio
async def test_create_ioc(client: AsyncClient, auth_headers, incident_id):
    response = await client.post(
        f"/api/v1/incidents/{incident_id}/iocs",
        json={"ioc_type": "ip", "value": "192.168.1.100", "confidence": 80},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["ioc_type"] == "ip"
    assert data["value"] == "192.168.1.100"
    assert data["confidence"] == 80


@pytest.mark.asyncio
async def test_bulk_import_iocs(client: AsyncClient, auth_headers, incident_id):
    text = "Attacker from 10.0.0.1, sent phish from bad@evil.com, C2 at https://c2.evil.com"
    response = await client.post(
        f"/api/v1/incidents/{incident_id}/iocs/bulk",
        json={"text": text},
        headers=auth_headers,
    )
    assert response.status_code == 201
    iocs = response.json()["data"]
    assert len(iocs) >= 2
    types = {i["ioc_type"] for i in iocs}
    assert "ip" in types
    assert "email" in types


@pytest.mark.asyncio
async def test_detect_iocs_without_saving(client: AsyncClient, auth_headers, incident_id):
    text = "Hash: " + "a" * 64
    response = await client.post(
        f"/api/v1/incidents/{incident_id}/iocs/detect",
        json={"text": text},
        headers=auth_headers,
    )
    assert response.status_code == 200
    detected = response.json()
    assert any(d["ioc_type"] == "hash" for d in detected)

    # Verify nothing was saved
    iocs = await client.get(f"/api/v1/incidents/{incident_id}/iocs", headers=auth_headers)
    assert iocs.json() == []


@pytest.mark.asyncio
async def test_update_ioc_status(client: AsyncClient, auth_headers, incident_id):
    create = await client.post(
        f"/api/v1/incidents/{incident_id}/iocs",
        json={"ioc_type": "domain", "value": "evil.com"},
        headers=auth_headers,
    )
    ioc_id = create.json()["data"]["id"]
    response = await client.put(
        f"/api/v1/incidents/{incident_id}/iocs/{ioc_id}",
        json={"status": "blocked"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "blocked"
