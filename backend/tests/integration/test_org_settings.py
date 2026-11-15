"""PUT /admin/org: saving org settings from the admin form (Refs #167, #170)."""
import pytest
from httpx import AsyncClient

# Exactly what OrgSettingsPage.handleSave sends for an org with no logo.
FORM_PAYLOAD = {
    "name": "Acme SOC",
    "allow_registration": False,
    "logo_url": "",
    "accent_color": "#6366f1",
    "session_idle_minutes": 0,
    "session_max_hours": 0,
}


@pytest.mark.asyncio
async def test_form_payload_without_logo_renames_org(client: AsyncClient, auth_headers):
    resp = await client.put("/api/v1/admin/org", json=FORM_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 200, resp.text

    org = (await client.get("/api/v1/admin/org", headers=auth_headers)).json()["data"]
    assert org["name"] == "Acme SOC"
    assert not org["settings"].get("logo_url")


@pytest.mark.asyncio
async def test_logo_url_round_trips_as_string(client: AsyncClient, auth_headers):
    payload = {**FORM_PAYLOAD, "logo_url": "https://cdn.example.com/logo.png"}
    resp = await client.put("/api/v1/admin/org", json=payload, headers=auth_headers)
    assert resp.status_code == 200, resp.text

    org = (await client.get("/api/v1/admin/org", headers=auth_headers)).json()["data"]
    assert org["settings"]["logo_url"] == "https://cdn.example.com/logo.png"


@pytest.mark.asyncio
async def test_empty_logo_url_clears_a_saved_logo(client: AsyncClient, auth_headers):
    await client.put(
        "/api/v1/admin/org", json={"logo_url": "https://cdn.example.com/logo.png"}, headers=auth_headers,
    )
    resp = await client.put("/api/v1/admin/org", json={"logo_url": ""}, headers=auth_headers)
    assert resp.status_code == 200, resp.text

    org = (await client.get("/api/v1/admin/org", headers=auth_headers)).json()["data"]
    assert not org["settings"].get("logo_url")


@pytest.mark.asyncio
@pytest.mark.parametrize("patch", [
    {"logo_url": "not a url"},
    {"logo_url": "javascript:alert(1)"},
    {"logo_url": "ftp://example.com/logo.png"},
    {"accent_color": "red"},
    {"accent_color": "#12345"},
    {"name": "   "},
    {"name": "x" * 201},
])
async def test_invalid_values_are_rejected(client: AsyncClient, auth_headers, patch):
    resp = await client.put("/api/v1/admin/org", json={**FORM_PAYLOAD, **patch}, headers=auth_headers)
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_name_is_trimmed(client: AsyncClient, auth_headers):
    resp = await client.put("/api/v1/admin/org", json={"name": "  Acme  "}, headers=auth_headers)
    assert resp.status_code == 200
    org = (await client.get("/api/v1/admin/org", headers=auth_headers)).json()["data"]
    assert org["name"] == "Acme"
