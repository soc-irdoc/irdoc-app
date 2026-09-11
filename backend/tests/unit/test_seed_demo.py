"""
Tests for the demo-only seeder (seed_demo.py).

Unlike seed.py, this script IS expected to create an org, 4 users, and a
batch of incidents — it's only ever run explicitly against the throwaway
demo.irdoc.io database, never wired into entrypoint.sh. See seed_demo.py's
module docstring for why it has to stay a separate script from seed.py.
"""
from sqlalchemy import select

import seed as seed_module
import seed_demo as seed_demo_module
from app.models.incident import Incident
from app.models.organization import Organization
from app.models.task import Task
from app.models.timeline import TimelineEntry
from app.models.user import User


async def _seed_templates_and_demo(db_session, monkeypatch):
    # seed_demo.py assumes seed.py's system templates already exist (same as
    # a real container boot: entrypoint.sh runs seed.py before anything else).
    monkeypatch.setattr(seed_module, "AsyncSessionLocal", lambda: db_session)
    await seed_module.seed()
    await db_session.commit()

    monkeypatch.setattr(seed_demo_module, "AsyncSessionLocal", lambda: db_session)
    await seed_demo_module.seed_demo()
    await db_session.commit()


async def test_seed_demo_creates_org_and_four_role_accounts(db_session, monkeypatch):
    await _seed_templates_and_demo(db_session, monkeypatch)

    orgs = (await db_session.execute(select(Organization))).scalars().all()
    assert len(orgs) == 1

    users = (await db_session.execute(select(User))).scalars().all()
    assert {u.role for u in users} == {"admin", "senior_analyst", "analyst", "viewer"}
    assert {u.email for u in users} == {
        "admin@irdoc.io", "senior_analyst@irdoc.io", "analyst@irdoc.io", "viewer@irdoc.io",
    }


async def test_seed_demo_creates_incidents_across_all_statuses_and_categories(db_session, monkeypatch):
    await _seed_templates_and_demo(db_session, monkeypatch)

    incidents = (await db_session.execute(select(Incident))).scalars().all()
    assert len(incidents) == len(seed_demo_module.INCIDENT_SCENARIOS)
    assert {i.status for i in incidents} == {"open", "monitoring", "contained", "closed"}
    assert len({i.template_id for i in incidents}) == 4  # all 4 system templates used
    assert len({i.incident_ref for i in incidents}) == len(incidents)  # refs are unique

    # Every incident should have at least a detection timeline entry.
    timeline_count = (await db_session.execute(select(TimelineEntry))).scalars().all()
    assert len(timeline_count) >= len(incidents)

    # Closed incidents should have all their seeded tasks marked done.
    closed = [i for i in incidents if i.status == "closed"]
    assert closed, "expected at least one closed demo incident"
    closed_tasks = (
        await db_session.execute(select(Task).where(Task.incident_id == closed[0].id))
    ).scalars().all()
    assert closed_tasks
    assert all(t.status == "done" for t in closed_tasks)


async def test_seed_demo_is_idempotent(db_session, monkeypatch):
    await _seed_templates_and_demo(db_session, monkeypatch)

    # Second run must be a no-op (mirrors what happens if entrypoint.sh's own
    # seed.py re-runs on a container restart without the DB being wiped first).
    await seed_demo_module.seed_demo()
    await db_session.commit()

    users = (await db_session.execute(select(User))).scalars().all()
    incidents = (await db_session.execute(select(Incident))).scalars().all()
    assert len(users) == 4
    assert len(incidents) == len(seed_demo_module.INCIDENT_SCENARIOS)


async def test_seed_demo_respects_password_env_overrides(db_session, monkeypatch):
    monkeypatch.setenv("DEMO_PASSWORD", "SharedFallback123!")
    monkeypatch.setenv("DEMO_ADMIN_PASSWORD", "AdminOnly123!")
    await _seed_templates_and_demo(db_session, monkeypatch)

    from app.core.security import verify_password

    admin = (await db_session.execute(select(User).where(User.role == "admin"))).scalar_one()
    viewer = (await db_session.execute(select(User).where(User.role == "viewer"))).scalar_one()
    assert verify_password("AdminOnly123!", admin.password_hash)
    assert verify_password("SharedFallback123!", viewer.password_hash)
