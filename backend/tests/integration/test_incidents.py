"""Integration tests for incident CRUD."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_incident(client: AsyncClient, auth_headers):
    response = await client.post(
        "/api/v1/incidents",
        json={"title": "Test Incident", "severity": "sev2"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["title"] == "Test Incident"
    assert data["severity"] == "sev2"
    assert data["incident_ref"].startswith("INC-")


@pytest.mark.asyncio
async def test_list_incidents(client: AsyncClient, auth_headers):
    await client.post(
        "/api/v1/incidents",
        json={"title": "Incident A", "severity": "sev1"},
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/incidents",
        json={"title": "Incident B", "severity": "sev3"},
        headers=auth_headers,
    )
    response = await client.get("/api/v1/incidents", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 2


@pytest.mark.asyncio
async def test_get_incident(client: AsyncClient, auth_headers):
    create = await client.post(
        "/api/v1/incidents",
        json={"title": "Get Me", "severity": "sev2"},
        headers=auth_headers,
    )
    iid = create.json()["data"]["id"]
    response = await client.get(f"/api/v1/incidents/{iid}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["id"] == iid


@pytest.mark.asyncio
async def test_update_incident(client: AsyncClient, auth_headers):
    create = await client.post(
        "/api/v1/incidents",
        json={"title": "Update Me", "severity": "sev2"},
        headers=auth_headers,
    )
    iid = create.json()["data"]["id"]
    response = await client.put(
        f"/api/v1/incidents/{iid}",
        json={"status": "contained", "executive_summary": "Contained quickly."},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "contained"
    assert data["contained_at"] is not None


@pytest.mark.asyncio
async def test_filter_by_status(client: AsyncClient, auth_headers):
    await client.post("/api/v1/incidents", json={"title": "Open", "severity": "sev2"}, headers=auth_headers)
    r2 = await client.post("/api/v1/incidents", json={"title": "Closed", "severity": "sev3"}, headers=auth_headers)
    iid = r2.json()["data"]["id"]
    await client.put(f"/api/v1/incidents/{iid}", json={"status": "closed"}, headers=auth_headers)

    response = await client.get("/api/v1/incidents?status=closed", headers=auth_headers)
    assert response.json()["meta"]["total"] == 1


@pytest.mark.asyncio
async def test_incident_ref_sequential(client: AsyncClient, auth_headers):
    r1 = await client.post("/api/v1/incidents", json={"title": "A", "severity": "sev1"}, headers=auth_headers)
    r2 = await client.post("/api/v1/incidents", json={"title": "B", "severity": "sev1"}, headers=auth_headers)
    ref1 = r1.json()["data"]["incident_ref"]
    ref2 = r2.json()["data"]["incident_ref"]
    # Both should be INC-YYYY-NNNN format
    assert ref1 != ref2
    assert ref1.startswith("INC-")
