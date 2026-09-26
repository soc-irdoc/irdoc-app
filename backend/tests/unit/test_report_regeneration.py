"""
Automatic report regeneration after incident changes (issue #58).

Once a report has been generated manually for an incident, every later change
to that incident must produce a new report version — regardless of whether AI
or SharePoint are enabled. AI and SharePoint only change *how* the new version
is produced (AI narrative, push to a document library), never *whether* it is.

No external service is contacted: Redis is replaced by an in-memory fake,
Celery dispatch is patched, and SharePoint/AI are represented only by their
DB configuration rows. The SharePoint push itself is covered by
test_sharepoint_plugin.py.
"""
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models.ai_config import AiConfig
from app.models.incident import Incident
from app.models.integration import OrgIntegration
from app.models.report import Report
from app.models.template import ReportTemplate
from app.services import report_regen_service as regen


class FakeRedis:
    """Just enough of redis-py's sync client for the debounce token."""

    def __init__(self):
        self.store: dict[str, bytes] = {}
        self.ttls: dict[str, int] = {}

    def set(self, key, value, ex=None):
        self.store[key] = value.encode() if isinstance(value, str) else value
        self.ttls[key] = ex
        return True

    def get(self, key):
        return self.store.get(key)

    def close(self):
        pass


@pytest.fixture
def fake_redis():
    r = FakeRedis()
    with patch.object(regen, "_redis_client", return_value=r):
        yield r


@pytest.fixture
def scheduled():
    """Captures auto_regenerate_reports.apply_async calls."""
    with patch("app.workers.tasks.auto_regenerate_reports.apply_async") as m:
        yield m


@pytest.fixture
async def org_and_incident(db_session, admin_user):
    user, org = admin_user
    incident = Incident(org_id=org.id, incident_ref="INC-REGEN-1", title="Regen test")
    db_session.add(incident)
    await db_session.commit()
    return user, org, incident


async def _template(db, org, *, ai_auto_generate=False, name="Mgmt"):
    t = ReportTemplate(org_id=org.id, name=name, ai_auto_generate=ai_auto_generate, schema_json=[])
    db.add(t)
    await db.commit()
    return t


async def _manual_report(db, incident, user, template=None, classification="confidential"):
    r = Report(
        incident_id=incident.id,
        report_template_id=template.id if template else None,
        report_type="pdf",
        classification=classification,
        generated_by=user.id,
        status="ready",
        version_number=1,
    )
    db.add(r)
    await db.commit()
    return r


async def _enable_ai(db, org, debounce=30):
    db.add(AiConfig(org_id=org.id, is_enabled=True, debounce_seconds=debounce))
    await db.commit()


async def _enable_sharepoint(db, org, debounce="45"):
    db.add(OrgIntegration(
        org_id=org.id, plugin_name="sharepoint", is_enabled=True,
        config={"debounce_seconds": debounce},
    ))
    await db.commit()


async def _reports_for(db, incident):
    res = await db.execute(
        select(Report).where(Report.incident_id == incident.id).order_by(Report.created_at)
    )
    return list(res.scalars().all())


# ─── Trigger / debounce ────────────────────────────────────────────────────────

class TestTrigger:
    async def test_schedules_regen_with_default_debounce_when_nothing_enabled(
        self, db_session, org_and_incident, fake_redis, scheduled
    ):
        _, org, incident = org_and_incident
        await regen.maybe_trigger_report_regen(db_session, str(incident.id), str(org.id))

        scheduled.assert_called_once()
        kwargs = scheduled.call_args.kwargs
        assert kwargs["countdown"] == regen.DEFAULT_DEBOUNCE_SECONDS == 600  # #71: 10 minutes
        incident_id, org_id, token = kwargs["args"]
        assert (incident_id, org_id) == (str(incident.id), str(org.id))
        assert fake_redis.get(regen.regen_token_key(str(incident.id))) == token.encode()

    async def test_uses_ai_debounce_when_ai_enabled(
        self, db_session, org_and_incident, fake_redis, scheduled
    ):
        _, org, incident = org_and_incident
        await _enable_ai(db_session, org, debounce=30)
        await _enable_sharepoint(db_session, org, debounce="45")
        await regen.maybe_trigger_report_regen(db_session, str(incident.id), str(org.id))
        assert scheduled.call_args.kwargs["countdown"] == 30

    async def test_uses_sharepoint_debounce_when_only_sharepoint_enabled(
        self, db_session, org_and_incident, fake_redis, scheduled
    ):
        _, org, incident = org_and_incident
        await _enable_sharepoint(db_session, org, debounce="45")
        await regen.maybe_trigger_report_regen(db_session, str(incident.id), str(org.id))
        assert scheduled.call_args.kwargs["countdown"] == 45

    async def test_token_outlives_the_countdown(
        self, db_session, org_and_incident, fake_redis, scheduled
    ):
        _, org, incident = org_and_incident
        await regen.maybe_trigger_report_regen(db_session, str(incident.id), str(org.id))
        ttl = fake_redis.ttls[regen.regen_token_key(str(incident.id))]
        assert ttl > scheduled.call_args.kwargs["countdown"]

    async def test_latest_change_wins(self, db_session, org_and_incident, fake_redis, scheduled):
        """Trailing-edge debounce: only the most recently scheduled run may proceed."""
        _, org, incident = org_and_incident
        await regen.maybe_trigger_report_regen(db_session, str(incident.id), str(org.id))
        first_token = scheduled.call_args.kwargs["args"][2]
        await regen.maybe_trigger_report_regen(db_session, str(incident.id), str(org.id))
        second_token = scheduled.call_args.kwargs["args"][2]

        assert first_token != second_token
        assert not regen.is_latest_token(fake_redis, str(incident.id), first_token)
        assert regen.is_latest_token(fake_redis, str(incident.id), second_token)

    async def test_never_raises_into_the_caller(self, db_session, org_and_incident, scheduled):
        _, org, incident = org_and_incident
        with patch.object(regen, "_redis_client", side_effect=ConnectionError("redis down")):
            await regen.maybe_trigger_report_regen(db_session, str(incident.id), str(org.id))
        scheduled.assert_not_called()


# ─── Regeneration planning (all AI × SharePoint combinations) ─────────────────

class TestCreateRegenerationReports:
    async def test_no_manual_report_means_no_regeneration(self, db_session, org_and_incident):
        _, org, incident = org_and_incident
        jobs = await regen.create_regeneration_reports(db_session, str(incident.id), str(org.id))
        assert jobs == []
        assert await _reports_for(db_session, incident) == []

    async def test_plain_install_regenerates_seeded_template(self, db_session, org_and_incident):
        """The reported bug: no AI, no SharePoint → a new version must still be produced."""
        user, org, incident = org_and_incident
        tmpl = await _template(db_session, org)
        await _manual_report(db_session, incident, user, tmpl, classification="restricted")

        jobs = await regen.create_regeneration_reports(db_session, str(incident.id), str(org.id))

        assert len(jobs) == 1
        assert jobs[0].include_ai is False
        assert jobs[0].trigger_sharepoint is False
        reports = await _reports_for(db_session, incident)
        new = next(r for r in reports if str(r.id) == jobs[0].report_id)
        assert new.status == "pending"
        assert new.report_template_id == tmpl.id
        assert new.version_number == 2
        assert new.is_ai_assisted is False
        # carries over who/what the analyst chose for the manual report
        assert new.generated_by == user.id
        assert new.classification == "restricted"

    async def test_base_report_without_template_is_regenerated(self, db_session, org_and_incident):
        user, org, incident = org_and_incident
        await _manual_report(db_session, incident, user, template=None)

        jobs = await regen.create_regeneration_reports(db_session, str(incident.id), str(org.id))

        assert len(jobs) == 1
        new = (await db_session.execute(select(Report).where(Report.id == jobs[0].report_id))).scalar_one()
        assert new.report_template_id is None
        assert new.version_number == 2

    async def test_one_new_version_per_seeded_template(self, db_session, org_and_incident):
        user, org, incident = org_and_incident
        a = await _template(db_session, org, name="A")
        b = await _template(db_session, org, name="B")
        await _manual_report(db_session, incident, user, a)
        await _manual_report(db_session, incident, user, a)  # two versions of A already
        await _manual_report(db_session, incident, user, b)

        jobs = await regen.create_regeneration_reports(db_session, str(incident.id), str(org.id))

        assert len(jobs) == 2
        by_tmpl = {}
        for job in jobs:
            r = (await db_session.execute(select(Report).where(Report.id == job.report_id))).scalar_one()
            by_tmpl[r.report_template_id] = r.version_number
        # both existing A reports are v1 in the fixture, so max+1 == 2
        assert by_tmpl == {a.id: 2, b.id: 2}

    async def test_ai_enabled_and_template_flagged_uses_ai(self, db_session, org_and_incident):
        user, org, incident = org_and_incident
        await _enable_ai(db_session, org)
        tmpl = await _template(db_session, org, ai_auto_generate=True)
        await _manual_report(db_session, incident, user, tmpl)

        with patch.object(regen, "check_feature", return_value=True):
            jobs = await regen.create_regeneration_reports(db_session, str(incident.id), str(org.id))

        assert [j.include_ai for j in jobs] == [True]
        new = (await db_session.execute(select(Report).where(Report.id == jobs[0].report_id))).scalar_one()
        assert new.is_ai_assisted is True

    async def test_ai_enabled_but_template_not_flagged_still_regenerates_without_ai(
        self, db_session, org_and_incident
    ):
        """Previously skipped entirely by generate_ai_report."""
        user, org, incident = org_and_incident
        await _enable_ai(db_session, org)
        tmpl = await _template(db_session, org, ai_auto_generate=False)
        await _manual_report(db_session, incident, user, tmpl)

        with patch.object(regen, "check_feature", return_value=True):
            jobs = await regen.create_regeneration_reports(db_session, str(incident.id), str(org.id))

        assert [j.include_ai for j in jobs] == [False]

    async def test_ai_enabled_but_unlicensed_regenerates_without_ai(self, db_session, org_and_incident):
        user, org, incident = org_and_incident
        await _enable_ai(db_session, org)
        tmpl = await _template(db_session, org, ai_auto_generate=True)
        await _manual_report(db_session, incident, user, tmpl)

        with patch.object(regen, "check_feature", return_value=False):
            jobs = await regen.create_regeneration_reports(db_session, str(incident.id), str(org.id))

        assert [j.include_ai for j in jobs] == [False]

    async def test_sharepoint_enabled_pushes_new_version(self, db_session, org_and_incident):
        user, org, incident = org_and_incident
        await _enable_sharepoint(db_session, org)
        tmpl = await _template(db_session, org)
        await _manual_report(db_session, incident, user, tmpl)

        jobs = await regen.create_regeneration_reports(db_session, str(incident.id), str(org.id))

        assert [(j.include_ai, j.trigger_sharepoint) for j in jobs] == [(False, True)]

    async def test_sharepoint_disabled_integration_is_ignored(self, db_session, org_and_incident):
        user, org, incident = org_and_incident
        db_session.add(OrgIntegration(org_id=org.id, plugin_name="sharepoint", is_enabled=False, config={}))
        await db_session.commit()
        tmpl = await _template(db_session, org)
        await _manual_report(db_session, incident, user, tmpl)

        jobs = await regen.create_regeneration_reports(db_session, str(incident.id), str(org.id))

        assert [j.trigger_sharepoint for j in jobs] == [False]

    async def test_ai_and_sharepoint_both_enabled(self, db_session, org_and_incident):
        """Previously the SharePoint path bailed out when AI was on, so unflagged
        templates were neither regenerated nor pushed."""
        user, org, incident = org_and_incident
        await _enable_ai(db_session, org)
        await _enable_sharepoint(db_session, org)
        flagged = await _template(db_session, org, ai_auto_generate=True, name="Flagged")
        plain = await _template(db_session, org, ai_auto_generate=False, name="Plain")
        await _manual_report(db_session, incident, user, flagged)
        await _manual_report(db_session, incident, user, plain)

        with patch.object(regen, "check_feature", return_value=True):
            jobs = await regen.create_regeneration_reports(db_session, str(incident.id), str(org.id))

        got = {}
        for job in jobs:
            r = (await db_session.execute(select(Report).where(Report.id == job.report_id))).scalar_one()
            got[r.report_template_id] = (job.include_ai, job.trigger_sharepoint)
        assert got == {flagged.id: (True, True), plain.id: (False, True)}

    async def test_other_incidents_are_untouched(self, db_session, org_and_incident):
        user, org, incident = org_and_incident
        other = Incident(org_id=org.id, incident_ref="INC-REGEN-2", title="Other")
        db_session.add(other)
        await db_session.commit()
        tmpl = await _template(db_session, org)
        await _manual_report(db_session, other, user, tmpl)

        jobs = await regen.create_regeneration_reports(db_session, str(incident.id), str(org.id))

        assert jobs == []


# ─── Versioning ────────────────────────────────────────────────────────────────

class TestVersioning:
    async def test_first_version_is_one(self, db_session, org_and_incident):
        _, org, incident = org_and_incident
        tmpl = await _template(db_session, org)
        assert await regen.next_version_number(db_session, incident.id, tmpl.id) == 1

    async def test_versions_are_scoped_per_template(self, db_session, org_and_incident):
        user, org, incident = org_and_incident
        a = await _template(db_session, org, name="A")
        b = await _template(db_session, org, name="B")
        r = await _manual_report(db_session, incident, user, a)
        r.version_number = 4
        await db_session.commit()

        assert await regen.next_version_number(db_session, incident.id, a.id) == 5
        assert await regen.next_version_number(db_session, incident.id, b.id) == 1

    async def test_base_reports_have_their_own_sequence(self, db_session, org_and_incident):
        user, org, incident = org_and_incident
        a = await _template(db_session, org)
        r = await _manual_report(db_session, incident, user, a)
        r.version_number = 3
        await db_session.commit()
        await _manual_report(db_session, incident, user, template=None)

        assert await regen.next_version_number(db_session, incident.id, None) == 2

    async def test_manual_generation_increments_version(
        self, client, auth_headers, db_session, admin_user
    ):
        """Manual (non-AI) reports used to stay at v1 forever."""
        _, org = admin_user
        tmpl = await _template(db_session, org)
        inc = await client.post(
            "/api/v1/incidents", json={"title": "Versioned", "severity": "sev3"}, headers=auth_headers
        )
        incident_id = inc.json()["data"]["id"]

        with patch("app.services.report_service.generate_report.delay"):
            versions = []
            for _ in range(2):
                resp = await client.post(
                    f"/api/v1/incidents/{incident_id}/reports",
                    json={"format": "pdf", "report_template_id": str(tmpl.id), "include_ai": False},
                    headers=auth_headers,
                )
                assert resp.status_code in (200, 201, 202), resp.text
                versions.append(resp.json()["data"]["version_number"])

        assert versions == [1, 2]


# ─── Celery task wiring ────────────────────────────────────────────────────────

class TestTask:
    async def test_stale_token_skips_regeneration(self, db_session, org_and_incident, fake_redis):
        user, org, incident = org_and_incident
        tmpl = await _template(db_session, org)
        await _manual_report(db_session, incident, user, tmpl)
        fake_redis.set(regen.regen_token_key(str(incident.id)), "newer-token")

        from app.workers import tasks
        with patch.object(tasks.generate_report, "apply_async") as dispatch:
            await tasks._auto_regenerate_reports(
                str(incident.id), str(org.id), "older-token", session_factory=_session_factory(db_session)
            )

        dispatch.assert_not_called()
        assert len(await _reports_for(db_session, incident)) == 1

    async def test_latest_token_dispatches_generate_report(self, db_session, org_and_incident, fake_redis):
        user, org, incident = org_and_incident
        await _enable_sharepoint(db_session, org)
        tmpl = await _template(db_session, org)
        await _manual_report(db_session, incident, user, tmpl)
        fake_redis.set(regen.regen_token_key(str(incident.id)), "tok")

        from app.workers import tasks
        with patch.object(tasks.generate_report, "apply_async") as dispatch:
            await tasks._auto_regenerate_reports(
                str(incident.id), str(org.id), "tok", session_factory=_session_factory(db_session)
            )

        dispatch.assert_called_once()
        kwargs = dispatch.call_args.kwargs
        new_id = kwargs["args"][0]
        assert kwargs["kwargs"] == {"include_ai": False, "org_id": str(org.id), "trigger_sharepoint": True}
        new = (await db_session.execute(select(Report).where(Report.id == new_id))).scalar_one()
        assert new.status == "pending"

    def test_task_is_routed_to_a_consumed_queue(self):
        from app.workers.celery_app import celery_app
        route = celery_app.conf.task_routes["app.workers.tasks.auto_regenerate_reports"]
        assert route["queue"] in {"default", "reports", "enrichment", "ai"}


def _session_factory(session):
    """Hands the test session to code that expects `async with factory() as db`."""
    class _Ctx:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *exc):
            return False

    return lambda: _Ctx()


# ─── Endpoint hooks ────────────────────────────────────────────────────────────

class TestEndpointsTriggerRegeneration:
    @pytest.fixture
    def hook(self):
        with patch("app.services.report_regen_service.maybe_trigger_report_regen") as m:
            yield m

    @pytest.fixture
    async def incident_id(self, client, auth_headers):
        r = await client.post(
            "/api/v1/incidents", json={"title": "Hooked", "severity": "sev2"}, headers=auth_headers
        )
        return r.json()["data"]["id"]

    async def _timeline_entry(self, client, auth_headers, incident_id):
        r = await client.post(
            f"/api/v1/incidents/{incident_id}/timeline",
            json={"entry_type": "analysis", "occurred_at": datetime.now(UTC).isoformat(), "description": "x"},
            headers=auth_headers,
        )
        return r.json()["data"]["id"]

    async def test_incident_update(self, client, auth_headers, incident_id, hook):
        r = await client.put(f"/api/v1/incidents/{incident_id}", json={"title": "Renamed"}, headers=auth_headers)
        assert r.status_code == 200
        hook.assert_awaited()

    async def test_timeline_create_update_delete(self, client, auth_headers, incident_id, hook):
        entry_id = await self._timeline_entry(client, auth_headers, incident_id)
        assert hook.await_count == 1

        r = await client.put(
            f"/api/v1/incidents/{incident_id}/timeline/{entry_id}",
            json={"description": "edited"}, headers=auth_headers,
        )
        assert r.status_code == 200
        assert hook.await_count == 2

        r = await client.delete(f"/api/v1/incidents/{incident_id}/timeline/{entry_id}", headers=auth_headers)
        assert r.status_code == 204
        assert hook.await_count == 3

    async def test_ioc_create_update_delete(self, client, auth_headers, incident_id, hook):
        r = await client.post(
            f"/api/v1/incidents/{incident_id}/iocs",
            json={"ioc_type": "ip", "value": "203.0.113.7"}, headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        ioc_id = r.json()["data"]["id"]
        assert hook.await_count == 1

        r = await client.put(
            f"/api/v1/incidents/{incident_id}/iocs/{ioc_id}", json={"description": "c2"}, headers=auth_headers
        )
        assert r.status_code == 200, r.text
        assert hook.await_count == 2

        r = await client.delete(f"/api/v1/incidents/{incident_id}/iocs/{ioc_id}", headers=auth_headers)
        assert r.status_code == 204
        assert hook.await_count == 3

    async def test_task_create_update_delete(self, client, auth_headers, incident_id, hook):
        r = await client.post(
            f"/api/v1/incidents/{incident_id}/tasks", json={"title": "Isolate host"}, headers=auth_headers
        )
        assert r.status_code == 201, r.text
        task_id = r.json()["data"]["id"]

        r = await client.put(
            f"/api/v1/incidents/{incident_id}/tasks/{task_id}", json={"status": "done"}, headers=auth_headers
        )
        assert r.status_code == 200, r.text

        r = await client.delete(f"/api/v1/incidents/{incident_id}/tasks/{task_id}", headers=auth_headers)
        assert r.status_code == 204
        assert hook.await_count == 3
