"""Time spent on a timeline entry: optional, 0-1440 minutes, clearable
(Refs #165)."""
import pytest

from tests.integration.test_evidence import _incident


async def _create(client, headers, iid, **extra):
    return await client.post(
        f"/api/v1/incidents/{iid}/timeline",
        json={"entry_type": "analysis", "description": "Reviewed headers",
              "occurred_at": "2026-11-14T10:00:00Z", **extra},
        headers=headers,
    )


@pytest.mark.asyncio
async def test_time_spent_is_optional(client, auth_headers):
    iid = await _incident(client, auth_headers)
    r = await _create(client, auth_headers, iid)
    assert r.status_code == 201, r.text
    assert r.json()["data"]["time_spent_minutes"] is None  # not tracked, not zero


@pytest.mark.asyncio
async def test_time_spent_is_saved_updated_and_cleared(client, auth_headers):
    iid = await _incident(client, auth_headers)
    entry = (await _create(client, auth_headers, iid, time_spent_minutes=20)).json()["data"]
    assert entry["time_spent_minutes"] == 20

    url = f"/api/v1/incidents/{iid}/timeline/{entry['id']}"
    r = await client.put(url, json={"time_spent_minutes": 45}, headers=auth_headers)
    assert r.json()["data"]["time_spent_minutes"] == 45

    # Editing something else leaves it alone
    r = await client.put(url, json={"description": "Reviewed headers and body"}, headers=auth_headers)
    assert r.json()["data"]["time_spent_minutes"] == 45

    # An explicit null clears it
    r = await client.put(url, json={"time_spent_minutes": None}, headers=auth_headers)
    assert r.json()["data"]["time_spent_minutes"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("minutes", [-1, 1441, 2.5, "ten"])
async def test_time_spent_out_of_range_is_422(client, auth_headers, minutes):
    iid = await _incident(client, auth_headers)
    r = await _create(client, auth_headers, iid, time_spent_minutes=minutes)
    assert r.status_code == 422
