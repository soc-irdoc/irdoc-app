"""Incidents list: server-side pagination and sorting (#127, #128)."""
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.models.incident import Incident
from app.models.user import User

URL = "/api/v1/incidents"


async def _seed(db_session, org, rows):
    """rows: dicts of title/severity/status/assigned_to; created 1 minute apart, oldest first."""
    start = datetime(2026, 10, 1, tzinfo=UTC)
    for i, row in enumerate(rows):
        db_session.add(Incident(
            org_id=org.id,
            incident_ref=f"INC-2026-{i + 1:04d}",
            title=row.get("title", f"Incident {i + 1}"),
            severity=row.get("severity", "medium"),
            status=row.get("status", "open"),
            disposition="fp_benign" if row.get("status") == "closed" else None,
            assigned_to=row.get("assigned_to"),
            created_at=start + timedelta(minutes=i),
            attack_vector=[],
            metadata_={},
        ))
    await db_session.flush()


async def _user(db_session, org, name):
    user = User(
        org_id=org.id,
        email=f"{name.lower().replace(' ', '.')}@test.com",
        full_name=name,
        role="analyst",
        password_hash=hash_password("TestPass123!"),
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _titles(client, headers, **params):
    response = await client.get(URL, params=params, headers=headers)
    assert response.status_code == 200, response.text
    return [i["title"] for i in response.json()["data"]], response.json()["meta"]


@pytest.mark.asyncio
async def test_pages_and_total(client: AsyncClient, auth_headers, db_session, admin_user):
    _, org = admin_user
    await _seed(db_session, org, [{} for _ in range(30)])

    titles, meta = await _titles(client, auth_headers, page=2, per_page=25)

    assert meta == {"page": 2, "per_page": 25, "total": 30}
    # Newest first by default: page 2 holds the 5 oldest.
    assert titles == [f"Incident {n}" for n in range(5, 0, -1)]


@pytest.mark.asyncio
async def test_default_page_size_is_25(client: AsyncClient, auth_headers, db_session, admin_user):
    _, org = admin_user
    await _seed(db_session, org, [{} for _ in range(30)])

    titles, meta = await _titles(client, auth_headers)

    assert len(titles) == 25
    assert meta["per_page"] == 25


@pytest.mark.asyncio
async def test_severity_sort_covers_all_pages(client: AsyncClient, auth_headers, db_session, admin_user):
    """Page 1 of a severity sort holds the most severe incidents of all pages,
    not just the ones that were already on page 1."""
    _, org = admin_user
    rows = [{"title": f"low {n}", "severity": "low"} for n in range(12)]
    rows += [{"title": "the critical one", "severity": "critical"}]
    rows = [{"title": "oldest critical", "severity": "critical"}] + rows  # would be last by date
    rows += [{"title": f"medium {n}", "severity": "medium"} for n in range(3)]
    rows += [{"title": "high one", "severity": "high"}]
    await _seed(db_session, org, rows)

    titles, _ = await _titles(client, auth_headers, sort="severity", order="desc", per_page=5)

    assert titles[:2] == ["the critical one", "oldest critical"]  # newest first within a level
    assert titles[2] == "high one"
    assert titles[3:] == ["medium 2", "medium 1"]

    titles, _ = await _titles(client, auth_headers, sort="severity", order="asc", per_page=5)
    assert all(t.startswith("low") for t in titles)


@pytest.mark.asyncio
async def test_status_sorts_by_workflow_order(client: AsyncClient, auth_headers, db_session, admin_user):
    _, org = admin_user
    await _seed(db_session, org, [
        {"title": "closed", "status": "closed"},
        {"title": "monitoring", "status": "monitoring"},
        {"title": "open", "status": "open"},
        {"title": "contained", "status": "contained"},
    ])

    titles, _ = await _titles(client, auth_headers, sort="status", order="asc")
    assert titles == ["open", "contained", "monitoring", "closed"]

    titles, _ = await _titles(client, auth_headers, sort="status", order="desc")
    assert titles == ["closed", "monitoring", "contained", "open"]


@pytest.mark.asyncio
async def test_owner_sort_puts_unassigned_last(client: AsyncClient, auth_headers, db_session, admin_user):
    _, org = admin_user
    zoe = await _user(db_session, org, "zoe Zimmer")
    adam = await _user(db_session, org, "Adam Ant")
    await _seed(db_session, org, [
        {"title": "nobody"},
        {"title": "zoe's", "assigned_to": zoe.id},
        {"title": "adam's", "assigned_to": adam.id},
    ])

    titles, _ = await _titles(client, auth_headers, sort="owner", order="asc")
    assert titles == ["adam's", "zoe's", "nobody"]

    titles, _ = await _titles(client, auth_headers, sort="owner", order="desc")
    assert titles == ["zoe's", "adam's", "nobody"]


@pytest.mark.asyncio
async def test_title_and_ref_sort(client: AsyncClient, auth_headers, db_session, admin_user):
    _, org = admin_user
    await _seed(db_session, org, [{"title": "beta"}, {"title": "Alpha"}, {"title": "gamma"}])

    titles, _ = await _titles(client, auth_headers, sort="title", order="asc")
    assert titles == ["Alpha", "beta", "gamma"]  # case-insensitive

    titles, _ = await _titles(client, auth_headers, sort="ref", order="asc")
    assert titles == ["beta", "Alpha", "gamma"]


@pytest.mark.asyncio
async def test_sort_combines_with_filter_and_search(client: AsyncClient, auth_headers, db_session, admin_user):
    _, org = admin_user
    await _seed(db_session, org, [
        {"title": "phish low", "severity": "low"},
        {"title": "phish critical", "severity": "critical"},
        {"title": "phish closed critical", "severity": "critical", "status": "closed"},
        {"title": "malware critical", "severity": "critical"},
    ])

    titles, meta = await _titles(
        client, auth_headers, status="open", search="phish", sort="severity", order="desc"
    )

    assert titles == ["phish critical", "phish low"]
    assert meta["total"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("params", [
    {"sort": "nonsense"},
    {"order": "sideways"},
    {"status": "archived"},
    {"per_page": 101},
    {"page": 0},
])
async def test_invalid_list_params_rejected(client: AsyncClient, auth_headers, params):
    response = await client.get(URL, params=params, headers=auth_headers)
    assert response.status_code == 422
