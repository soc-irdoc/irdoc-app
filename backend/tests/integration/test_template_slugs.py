"""Incident template slugs: unique per org, editable, and resolved safely by
the inbound webhook (Refs #168, #169)."""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_api_key
from app.models.api_key import APIKey
from app.models.incident import Incident
from app.models.organization import Organization
from app.models.task import Task
from app.models.template import IncidentTemplate

URL = "/api/v1/templates/incident"


async def _tpl(db: AsyncSession, org_id, slug: str, **kw) -> IncidentTemplate:
    tpl = IncidentTemplate(
        org_id=org_id, name=kw.pop("name", slug.title()), slug=slug,
        is_system=org_id is None, tasks_json=kw.pop("tasks_json", [{"title": f"task from {slug}"}]), **kw,
    )
    db.add(tpl)
    await db.flush()
    return tpl


@pytest.fixture
async def api_key_headers(db_session: AsyncSession, admin_user):
    user, org = admin_user
    raw_key, key_prefix, key_hash = generate_api_key()
    db_session.add(APIKey(
        org_id=org.id, created_by=user.id, name="Webhook", key_prefix=key_prefix,
        key_hash=key_hash, scopes=["incidents:create"],
    ))
    await db_session.flush()
    return {"Authorization": f"ApiKey {raw_key}"}


async def _webhook(client, headers, template: str):
    return await client.post(
        "/api/v1/external/incidents",
        json={"title": "Webhook incident", "severity": "high", "template": template},
        headers=headers,
    )


async def _task_titles(db: AsyncSession, incident_id: str) -> list[str]:
    rows = await db.execute(select(Task.title).where(Task.incident_id == incident_id))
    return [r[0] for r in rows]


# ─── Create: format and uniqueness (#168) ─────────────────────────────────────

@pytest.mark.asyncio
async def test_create_with_duplicate_slug_is_409(client: AsyncClient, auth_headers):
    r1 = await client.post(URL, json={"name": "A", "slug": "phish"}, headers=auth_headers)
    assert r1.status_code == 201, r1.text
    r2 = await client.post(URL, json={"name": "B", "slug": "phish"}, headers=auth_headers)
    assert r2.status_code == 409
    assert "phish" in r2.json()["detail"]


@pytest.mark.asyncio
async def test_create_with_system_slug_is_409(client: AsyncClient, auth_headers, db_session):
    await _tpl(db_session, None, "ransomware")
    r = await client.post(URL, json={"name": "Mine", "slug": "ransomware"}, headers=auth_headers)
    assert r.status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize("slug", ["", "Has Caps", "with space", "-lead", "trail-", "a--b", "x" * 101, "ünï"])
async def test_create_with_malformed_slug_is_422(client: AsyncClient, auth_headers, slug):
    r = await client.post(URL, json={"name": "A", "slug": slug}, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_same_slug_is_fine_in_another_org(client: AsyncClient, auth_headers, db_session):
    other = Organization(name="Other", slug="other")
    db_session.add(other)
    await db_session.flush()
    await _tpl(db_session, other.id, "phish")
    r = await client.post(URL, json={"name": "A", "slug": "phish"}, headers=auth_headers)
    assert r.status_code == 201, r.text


@pytest.mark.asyncio
async def test_unknown_fields_are_rejected(client: AsyncClient, auth_headers):
    r = await client.post(URL, json={"name": "A", "slug": "a", "slugg": "typo"}, headers=auth_headers)
    assert r.status_code == 422


# ─── Clone naming ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_clone_slugs_are_readable_and_unique(client: AsyncClient, auth_headers, db_session):
    src = await _tpl(db_session, None, "phishing")
    a = (await client.post(f"{URL}/{src.id}/clone", headers=auth_headers)).json()["data"]
    b = (await client.post(f"{URL}/{src.id}/clone", headers=auth_headers)).json()["data"]
    assert a["slug"] == "phishing-copy"
    assert b["slug"] == "phishing-copy-2"


# ─── Edit slug (#169) ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_edit_slug_is_saved(client: AsyncClient, auth_headers, admin_user, db_session):
    tpl = await _tpl(db_session, admin_user[1].id, "phishing-copy")
    r = await client.put(f"{URL}/{tpl.id}", json={"name": "Finance", "slug": "phishing-finance", "tasks_json": []},
                         headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["slug"] == "phishing-finance"


@pytest.mark.asyncio
async def test_edit_slug_to_a_taken_one_is_409(client: AsyncClient, auth_headers, admin_user, db_session):
    await _tpl(db_session, admin_user[1].id, "taken")
    await _tpl(db_session, None, "system-one")
    tpl = await _tpl(db_session, admin_user[1].id, "mine")
    for slug in ("taken", "system-one"):
        r = await client.put(f"{URL}/{tpl.id}", json={"slug": slug}, headers=auth_headers)
        assert r.status_code == 409, slug


@pytest.mark.asyncio
async def test_saving_with_unchanged_slug_is_fine(client: AsyncClient, auth_headers, admin_user, db_session):
    tpl = await _tpl(db_session, admin_user[1].id, "mine")
    r = await client.put(f"{URL}/{tpl.id}", json={"name": "Renamed", "slug": "mine"}, headers=auth_headers)
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_system_template_slug_cannot_change(client: AsyncClient, auth_headers, db_session):
    tpl = await _tpl(db_session, None, "malware")
    r = await client.put(f"{URL}/{tpl.id}", json={"slug": "malware-2"}, headers=auth_headers)
    assert r.status_code == 403


# ─── Webhook lookup (#168) ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_webhook_uses_own_org_template(client, api_key_headers, admin_user, db_session):
    await _tpl(db_session, admin_user[1].id, "phish")
    r = await _webhook(client, api_key_headers, "phish")
    assert r.status_code == 201, r.text
    assert await _task_titles(db_session, r.json()["incident_id"]) == ["task from phish"]


@pytest.mark.asyncio
async def test_webhook_uses_system_template(client, api_key_headers, db_session):
    await _tpl(db_session, None, "ddos")
    r = await _webhook(client, api_key_headers, "ddos")
    assert r.status_code == 201, r.text
    assert await _task_titles(db_session, r.json()["incident_id"]) == ["task from ddos"]


@pytest.mark.asyncio
async def test_webhook_never_uses_another_orgs_template(client, api_key_headers, db_session):
    other = Organization(name="Other", slug="other")
    db_session.add(other)
    await db_session.flush()
    await _tpl(db_session, other.id, "secret-playbook")

    r = await _webhook(client, api_key_headers, "secret-playbook")
    assert r.status_code == 422
    count = (await db_session.execute(select(Incident).where(Incident.title == "Webhook incident"))).all()
    assert count == []


@pytest.mark.asyncio
async def test_webhook_unknown_slug_is_422(client, api_key_headers):
    r = await _webhook(client, api_key_headers, "no-such-template")
    assert r.status_code == 422
    assert "no-such-template" in r.text


@pytest.mark.asyncio
async def test_webhook_ignores_hidden_templates(client, api_key_headers, admin_user, db_session):
    await _tpl(db_session, admin_user[1].id, "retired", is_hidden=True)
    r = await _webhook(client, api_key_headers, "retired")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_webhook_finds_template_by_new_slug_after_rename(
    client, auth_headers, api_key_headers, admin_user, db_session
):
    tpl = await _tpl(db_session, admin_user[1].id, "old-name")
    r = await client.put(f"{URL}/{tpl.id}", json={"slug": "new-name"}, headers=auth_headers)
    assert r.status_code == 200
    r = await _webhook(client, api_key_headers, "new-name")
    assert r.status_code == 201, r.text
