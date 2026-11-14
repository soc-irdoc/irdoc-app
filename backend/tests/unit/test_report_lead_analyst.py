"""The report's Lead Analyst is the incident's assignee, not whoever generated
the report (Refs #173)."""
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident
from app.models.user import User
from app.services.report_renderer.engine import _build_jinja_env
from app.services.report_renderer.payload import build_report_payload

_env = _build_jinja_env()


async def _assignee(db: AsyncSession, org) -> User:
    user = User(
        org_id=org.id, email="jane.doe@test.com", full_name="Doe, Jane", role="analyst",
        password_hash="x", avatar_initials="DJ",
    )
    db.add(user)
    await db.flush()
    return user


@pytest.mark.asyncio
async def test_lead_analyst_is_the_assignee_not_the_generator(db_session: AsyncSession, admin_user):
    admin, org = admin_user
    assignee = await _assignee(db_session, org)
    incident = Incident(
        org_id=org.id, incident_ref="INC-LEAD-1", title="Lead", status="closed", assigned_to=assignee.id,
    )
    db_session.add(incident)
    await db_session.flush()

    payload = await build_report_payload(incident_id=str(incident.id), analyst=admin, db=db_session)

    assert payload.lead_analyst.id == assignee.id
    assert payload.analyst.id == admin.id  # still the generator, for the footer


@pytest.mark.asyncio
async def test_lead_analyst_falls_back_to_generator_when_unassigned(db_session: AsyncSession, admin_user):
    admin, org = admin_user
    incident = Incident(org_id=org.id, incident_ref="INC-LEAD-2", title="Lead")
    db_session.add(incident)
    await db_session.flush()

    payload = await build_report_payload(incident_id=str(incident.id), analyst=admin, db=db_session)

    assert payload.lead_analyst.id == admin.id


def test_cover_renders_lead_analyst():
    p = SimpleNamespace(
        incident=SimpleNamespace(
            incident_ref="INC-2026-0001", title="Phishing", affected_users=0, status="closed",
        ),
        severity_label="High",
        status_label="Closed",
        disposition_label=None,
        generated_at=datetime(2026, 11, 13, tzinfo=timezone.utc),
        duration_str="1 hour",
        ioc_count=0,
        entry_count=0,
        contained_at_str=None,
        closed_at_str=None,
        analyst=SimpleNamespace(full_name="Admin"),
        lead_analyst=SimpleNamespace(full_name="Doe, Jane"),
    )
    block = {"type": "cover", "fields": ["analyst.full_name"]}
    html = _env.get_template("reports/blocks/cover.html").render(block=block, p=p, brand={})

    assert "Lead Analyst" in html
    assert "Doe, Jane" in html
    assert "Admin" not in html
