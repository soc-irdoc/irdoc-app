"""Integration tests for timeline endpoints."""
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient


@pytest.fixture
async def incident_id(client: AsyncClient, auth_headers):
    r = await client.post(
        "/api/v1/incidents",
        json={"title": "Timeline Test Incident", "severity": "sev2"},
        headers=auth_headers,
    )
    return r.json()["data"]["id"]


@pytest.mark.asyncio
async def test_create_timeline_entry(client: AsyncClient, auth_headers, incident_id):
    response = await client.post(
        f"/api/v1/incidents/{incident_id}/timeline",
        json={
            "entry_type": "detection",
            "occurred_at": datetime.now(UTC).isoformat(),
            "description": "SIEM alert triggered for anomalous login.",
            "source": "sentinel",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["entry_type"] == "detection"
    assert data["source"] == "sentinel"


@pytest.mark.asyncio
async def test_list_timeline_entries(client: AsyncClient, auth_headers, incident_id):
    for entry_type in ["detection", "analysis", "containment"]:
        await client.post(
            f"/api/v1/incidents/{incident_id}/timeline",
            json={"entry_type": entry_type, "occurred_at": datetime.now(UTC).isoformat(), "description": f"Step: {entry_type}"},
            headers=auth_headers,
        )
    response = await client.get(f"/api/v1/incidents/{incident_id}/timeline", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 3


@pytest.mark.asyncio
async def test_filter_timeline_by_type(client: AsyncClient, auth_headers, incident_id):
    for entry_type in ["detection", "analysis", "detection"]:
        await client.post(
            f"/api/v1/incidents/{incident_id}/timeline",
            json={"entry_type": entry_type, "occurred_at": datetime.now(UTC).isoformat(), "description": "entry"},
            headers=auth_headers,
        )
    response = await client.get(
        f"/api/v1/incidents/{incident_id}/timeline?entry_type=detection", headers=auth_headers
    )
    assert response.json()["meta"]["total"] == 2


@pytest.mark.asyncio
async def test_csv_export(client: AsyncClient, auth_headers, incident_id):
    await client.post(
        f"/api/v1/incidents/{incident_id}/timeline",
        json={"entry_type": "note", "occurred_at": datetime.now(UTC).isoformat(), "description": "CSV test entry"},
        headers=auth_headers,
    )
    response = await client.get(
        f"/api/v1/incidents/{incident_id}/timeline/export/csv", headers=auth_headers
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "CSV test entry" in response.text
