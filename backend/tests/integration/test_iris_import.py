"""End-to-end IRIS import (app/cli/iris_import) against the test DB, replaying recorded IRIS 2.4.27 responses."""
import io
from datetime import UTC, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select

from app.cli.iris_import.__main__ import EXIT_USAGE, main
from app.cli.iris_import.client import IrisClient
from app.cli.iris_import.importer import ImportUserError, run_import
from app.cli.iris_import.mapping import load_mapping
from app.models.asset import Asset, AssetTimelineLink
from app.models.audit import AuditLog
from app.models.incident import Incident, IncidentExternalRef
from app.models.ioc import IOC, IOCTimelineLink
from app.models.timeline import TimelineEntry
from tests.fixtures import iris

IRIS_URL = "https://iris.test"


@pytest.fixture
async def importer_user(db_session, admin_user):
    # The importer commits/rolls back per case; with the test session that
    # releases/rolls back a savepoint, so the user must be committed first.
    await db_session.commit()
    # Plain values: the run's rollbacks expire ORM objects in this session.
    user = admin_user[0]
    return SimpleNamespace(id=user.id, org_id=user.org_id, email=user.email)


async def _run(db_session, user, *, transport=None, **kwargs):
    out = io.StringIO()
    async with IrisClient(IRIS_URL, "test-key", transport=transport or iris.transport()) as client:
        report = await run_import(db_session, client, user_email=user.email, mapping=load_mapping(),
                                  tz=ZoneInfo("UTC"), out=out, **kwargs)
    return report, out.getvalue()


async def _count(db_session, model) -> int:
    return (await db_session.execute(select(func.count()).select_from(model))).scalar_one()


async def _incident(db_session, ref) -> Incident:
    return (await db_session.execute(select(Incident).where(Incident.incident_ref == ref))).scalar_one()


async def test_imports_closed_cases_with_original_dates(db_session, importer_user):
    report, output = await _run(db_session, importer_user)

    assert sorted(ref for _, ref in report.imported) == ["INC-2025-482913", "INC-2025-482950"]
    assert report.skipped == [(4, "missing_soc_id", "")]
    assert report.open_cases == 2
    assert report.ok
    assert "IRIS #4: no SOC ticket ID" in output
    assert "ioc_type: mutex" in output  # unmapped value listed in the summary

    inc = await _incident(db_session, "INC-2025-482913")
    assert inc.status == "closed"
    assert inc.disposition == "tp_remediated" and inc.source == "other" and inc.severity == "high"
    assert inc.opened_at == datetime(2025, 3, 3, tzinfo=UTC)
    assert inc.created_at == datetime(2025, 3, 3, tzinfo=UTC)
    assert inc.closed_at == datetime(2025, 3, 7, tzinfo=UTC)
    assert inc.org_id == importer_user.org_id
    assert inc.created_by == importer_user.id and inc.assigned_to == importer_user.id
    assert inc.executive_summary.startswith("<h1>Executive summary</h1>")
    assert "<h2>Investigation / Triage</h2>" in inc.notes

    ext = (await db_session.execute(
        select(IncidentExternalRef).where(IncidentExternalRef.incident_id == inc.id)
    )).scalar_one()
    assert (ext.external_source, ext.external_ref, ext.external_url) == ("dfir_iris", "2", f"{IRIS_URL}/case?cid=2")


async def test_timeline_assets_iocs_and_links(db_session, importer_user):
    await _run(db_session, importer_user)
    inc = await _incident(db_session, "INC-2025-482913")

    entries = (await db_session.execute(
        select(TimelineEntry).where(TimelineEntry.incident_id == inc.id).order_by(TimelineEntry.occurred_at)
    )).scalars().all()
    assert [e.occurred_at for e in entries] == [
        datetime(2025, 3, 3, 7, 12, 45, tzinfo=UTC),
        datetime(2025, 3, 3, 7, 15, 2, 120000, tzinfo=UTC),
        datetime(2025, 3, 3, 10, 40, tzinfo=UTC),
        datetime(2025, 3, 4, 14, 0, tzinfo=UTC),
    ]
    assert all(e.source == "DFIR IRIS" and e.author_id == importer_user.id for e in entries)

    assets = (await db_session.execute(select(Asset).where(Asset.incident_id == inc.id))).scalars().all()
    iocs = (await db_session.execute(select(IOC).where(IOC.incident_id == inc.id))).scalars().all()
    assert len(assets) == 3
    assert len(iocs) == 5  # the mutex is kept in the notes instead

    first_entry = entries[0]
    linked_assets = (await db_session.execute(
        select(Asset.name).join(AssetTimelineLink, AssetTimelineLink.asset_id == Asset.id)
        .where(AssetTimelineLink.timeline_entry_id == first_entry.id)
    )).scalars().all()
    linked_iocs = (await db_session.execute(
        select(IOC.value).join(IOCTimelineLink, IOCTimelineLink.ioc_id == IOC.id)
        .where(IOCTimelineLink.timeline_entry_id == first_entry.id)
    )).scalars().all()
    assert sorted(linked_assets) == ["FIN-WS-042", "j.doe"]
    assert sorted(linked_iocs) == ["44d88612fea8a8f36de82e1278abb02f", "login-micros0ft.example"]

    # first_seen is the earliest linked event; unlinked IOCs fall back to the open date.
    by_value = {i.value: i for i in iocs}
    assert by_value["login-micros0ft.example"].first_seen == first_entry.occurred_at
    assert by_value["203.0.113.77"].first_seen == entries[1].occurred_at
    assert by_value["invoice_7731.html"].first_seen == inc.opened_at


async def test_writes_an_audit_entry_per_incident(db_session, importer_user):
    await _run(db_session, importer_user)
    rows = (await db_session.execute(
        select(AuditLog).where(AuditLog.action == "incident.imported")
    )).scalars().all()
    assert sorted(r.entity_label for r in rows) == ["INC-2025-482913", "INC-2025-482950"]
    assert all(r.actor_label == "dfir-iris-import" for r in rows)


async def test_rerun_skips_cases_already_imported(db_session, importer_user):
    await _run(db_session, importer_user)
    before = await _count(db_session, Incident)

    seen: list[str] = []
    report, output = await _run(db_session, importer_user, transport=iris.transport(seen=seen))

    # Already-imported cases are recognised before anything inside them is fetched.
    assert not [k for k in seen if k.endswith(("cid=2", "cid=3"))]
    assert report.imported == []
    assert sorted(r for _, r, _ in report.skipped) == ["already_imported", "already_imported", "missing_soc_id"]
    assert "already imported (INC-2025-482913)" in output
    assert await _count(db_session, Incident) == before


async def test_reference_taken_by_another_incident_is_skipped(db_session, importer_user):
    db_session.add(Incident(org_id=importer_user.org_id, incident_ref="INC-2025-482950", title="Existing"))
    await db_session.commit()

    report, _ = await _run(db_session, importer_user)

    assert [ref for _, ref in report.imported] == ["INC-2025-482913"]
    assert (3, "ref_taken", "INC-2025-482950") in report.skipped
    assert (await _incident(db_session, "INC-2025-482950")).title == "Existing"


async def test_dry_run_saves_nothing(db_session, importer_user):
    report, output = await _run(db_session, importer_user, dry_run=True)

    assert len(report.imported) == 2
    assert "DRY RUN" in output and "would import" in output
    for model in (Incident, TimelineEntry, Asset, IOC, IncidentExternalRef):
        assert await _count(db_session, model) == 0


async def test_one_failing_case_does_not_stop_the_others(db_session, importer_user):
    transport = iris.transport(fail={"/case/assets/list?cid=2"})

    report, output = await _run(db_session, importer_user, transport=transport)

    assert [case for case, _ in report.failed] == [2]
    assert not report.ok
    assert "FAIL  IRIS #2" in output
    assert [ref for _, ref in report.imported] == ["INC-2025-482950"]
    assert await _count(db_session, Incident) == 1


async def test_limit_caps_the_number_of_closed_cases(db_session, importer_user):
    report, _ = await _run(db_session, importer_user, limit=1)
    assert [case for case, _ in report.imported] == [2]


async def test_list_cases_follows_pagination():
    recorded = iris.load()
    page = recorded["/manage/cases/filter?page=1"]
    cases = page["data"]["cases"]
    responses = {
        **recorded,
        "/manage/cases/filter?page=1": {**page, "data": {"total": len(cases), "cases": cases[:2]}},
        "/manage/cases/filter?page=2": {**page, "data": {"total": len(cases), "cases": cases[2:]}},
    }
    async with IrisClient(IRIS_URL, "k", transport=iris.transport(responses)) as client:
        listed = await client.list_cases()
    assert [c["case_id"] for c in listed] == sorted(c["case_id"] for c in cases)


async def test_unknown_import_user_is_rejected(db_session, admin_user):
    async with IrisClient(IRIS_URL, "k", transport=iris.transport()) as client:
        with pytest.raises(ImportUserError, match="no IRDoc user"):
            await run_import(db_session, client, user_email="nobody@example.com", mapping=load_mapping(),
                             tz=ZoneInfo("UTC"), out=io.StringIO())


def test_cli_requires_api_key_and_valid_timezone(monkeypatch, capsys):
    monkeypatch.delenv("IRIS_API_KEY", raising=False)
    assert main(["--iris-url", IRIS_URL, "--import-user", "a@b.c"]) == EXIT_USAGE
    assert "IRIS_API_KEY" in capsys.readouterr().err

    monkeypatch.setenv("IRIS_API_KEY", "k")
    assert main(["--iris-url", IRIS_URL, "--import-user", "a@b.c", "--date-tz", "Mars/Olympus"]) == EXIT_USAGE
    assert "unknown timezone" in capsys.readouterr().err
