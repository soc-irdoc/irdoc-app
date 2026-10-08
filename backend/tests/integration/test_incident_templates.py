"""Integration tests for incident template cloning (#81)."""
import pytest
from httpx import AsyncClient


async def _system_template(db_session):
    from app.models.template import IncidentTemplate
    tpl = IncidentTemplate(
        org_id=None,
        name="Phishing Attack",
        slug="phishing",
        description="Phishing playbook",
        is_system=True,
        tasks_json=[{"title": "Block sender", "phase": "containment"}],
    )
    db_session.add(tpl)
    await db_session.flush()
    return tpl


@pytest.mark.asyncio
async def test_clone_system_template_creates_editable_org_copy(
    client: AsyncClient, auth_headers, admin_user, db_session
):
    src = await _system_template(db_session)
    r = await client.post(f"/api/v1/templates/incident/{src.id}/clone", headers=auth_headers)
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    assert data["id"] != str(src.id)
    assert data["name"] == "Phishing Attack (Copy)"
    assert data["is_system"] is False
    assert data["org_id"] == str(admin_user[1].id)
    assert data["tasks_json"] == [{"title": "Block sender", "phase": "containment"}]
    assert data["slug"] != "phishing"

    # The copy is editable, unlike the system original.
    r = await client.put(
        f"/api/v1/templates/incident/{data['id']}", json={"name": "My Phishing"}, headers=auth_headers
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["name"] == "My Phishing"


@pytest.mark.asyncio
async def test_clone_twice_gives_distinct_slugs(client: AsyncClient, auth_headers, db_session):
    src = await _system_template(db_session)
    a = await client.post(f"/api/v1/templates/incident/{src.id}/clone", headers=auth_headers)
    b = await client.post(f"/api/v1/templates/incident/{src.id}/clone", headers=auth_headers)
    assert a.status_code == b.status_code == 201
    assert a.json()["data"]["slug"] != b.json()["data"]["slug"]


@pytest.mark.asyncio
async def test_clone_unknown_template_404(client: AsyncClient, auth_headers):
    r = await client.post(
        "/api/v1/templates/incident/00000000-0000-0000-0000-000000000000/clone", headers=auth_headers
    )
    assert r.status_code == 404
