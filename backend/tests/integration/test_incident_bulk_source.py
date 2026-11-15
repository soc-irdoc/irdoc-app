"""POST /incidents/bulk/source: fill in Source for many incidents at once
(Refs #153)."""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.incident import Incident
from app.models.organization import Organization

URL = "/api/v1/incidents/bulk/source"


async def _incident(db: AsyncSession, org_id, n: int, source: str | None = None) -> Incident:
    inc = Incident(
        org_id=org_id, incident_ref=f"INC-2026-{n:04d}", title=f"Incident {n}",
        source=source, attack_vector=[], metadata_={},
    )
    db.add(inc)
    await db.flush()
    return inc


async def _source(db: AsyncSession, inc: Incident) -> str | None:
    await db.refresh(inc)
    return inc.source


@pytest.mark.asyncio
async def test_sets_source_on_incidents_without_one(client: AsyncClient, auth_headers, admin_user, db_session):
    _, org = admin_user
    a = await _incident(db_session, org.id, 1)
    b = await _incident(db_session, org.id, 2)

    r = await client.post(URL, json={"ids": [str(a.id), str(b.id)], "source": "siem_alert"}, headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"updated": 2, "skipped": 0, "not_found": 0}
    assert await _source(db_session, a) == "siem_alert"
    assert await _source(db_session, b) == "siem_alert"


@pytest.mark.asyncio
async def test_existing_sources_are_kept_unless_overwrite(client: AsyncClient, auth_headers, admin_user, db_session):
    _, org = admin_user
    empty = await _incident(db_session, org.id, 1)
    has = await _incident(db_session, org.id, 2, source="email_security")
    ids = [str(empty.id), str(has.id)]

    r = await client.post(URL, json={"ids": ids, "source": "siem_alert"}, headers=auth_headers)
    assert r.json()["data"] == {"updated": 1, "skipped": 1, "not_found": 0}
    assert await _source(db_session, has) == "email_security"

    r = await client.post(URL, json={"ids": ids, "source": "other", "overwrite": True}, headers=auth_headers)
    assert r.json()["data"] == {"updated": 2, "skipped": 0, "not_found": 0}
    assert await _source(db_session, has) == "other"


@pytest.mark.asyncio
async def test_each_change_is_audited_with_the_old_value(client: AsyncClient, auth_headers, admin_user, db_session):
    _, org = admin_user
    a = await _incident(db_session, org.id, 1)
    b = await _incident(db_session, org.id, 2, source="cloud_alert")

    await client.post(URL, json={"ids": [str(a.id), str(b.id)], "source": "siem_alert", "overwrite": True},
                      headers=auth_headers)

    rows = (await db_session.execute(
        select(AuditLog).where(AuditLog.action == "incident.source_changed")
    )).scalars().all()
    diffs = {str(row.entity_id): row.diff for row in rows}
    assert diffs[str(a.id)]["from"] is None and diffs[str(a.id)]["to"] == "siem_alert"
    assert diffs[str(b.id)]["from"] == "cloud_alert"
    assert all(row.diff.get("bulk") is True for row in rows)
    assert all(row.actor_label == "admin@test.com" for row in rows)


@pytest.mark.asyncio
async def test_other_orgs_incidents_are_not_touched(client: AsyncClient, auth_headers, db_session):
    other = Organization(name="Other", slug="other")
    db_session.add(other)
    await db_session.flush()
    theirs = await _incident(db_session, other.id, 9)

    r = await client.post(URL, json={"ids": [str(theirs.id), str(uuid.uuid4())], "source": "siem_alert"},
                          headers=auth_headers)
    assert r.json()["data"] == {"updated": 0, "skipped": 0, "not_found": 2}
    assert await _source(db_session, theirs) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [
    {"ids": [], "source": "siem_alert"},
    {"ids": [str(uuid.uuid4())], "source": "not_a_source"},
    {"ids": [str(uuid.uuid4())] * 2, "source": None},
    {"ids": [str(uuid.uuid4()) for _ in range(501)], "source": "siem_alert"},
])
async def test_invalid_requests_are_422(client: AsyncClient, auth_headers, body):
    r = await client.post(URL, json=body, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_viewers_cannot_bulk_edit(client: AsyncClient, db_session, admin_user):
    from app.core.security import hash_password
    from app.models.user import User

    _, org = admin_user
    db_session.add(User(org_id=org.id, email="viewer@test.com", full_name="V", role="viewer",
                        password_hash=hash_password("TestPass123!"), avatar_initials="V"))
    await db_session.flush()
    login = await client.post("/api/v1/auth/login", json={"email": "viewer@test.com", "password": "TestPass123!"})
    token = login.json()["data"]["access_token"]
    inc = await _incident(db_session, org.id, 1)

    r = await client.post(URL, json={"ids": [str(inc.id)], "source": "siem_alert"},
                          headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
