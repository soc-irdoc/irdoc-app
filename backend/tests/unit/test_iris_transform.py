"""IRIS case -> IRDoc data (app/cli/iris_import/transform.py), on recorded IRIS 2.4.27 data."""
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from app.cli.iris_import.mapping import load_mapping
from app.cli.iris_import.transform import (
    SkipCase,
    build_case,
    build_iocs,
    build_ref,
    day_start_utc,
    strip_case_prefix,
)
from tests.fixtures import iris

UTC_TZ = ZoneInfo("UTC")
IRIS_URL = "https://iris.test"


def _case(case_id: int) -> dict:
    cases = iris.load()["/manage/cases/filter?page=1"]["data"]["cases"]
    return next(c for c in cases if c["case_id"] == case_id)


def _children(case_id: int) -> dict:
    """What IrisClient.fetch_children returns, rebuilt from the recording."""
    r = iris.load()
    q = f"?cid={case_id}"
    directories = r[f"/case/notes/directories/filter{q}"]["data"]
    notes = {n["id"]: r[f"/case/notes/{n['id']}{q}"]["data"] for d in directories for n in d["notes"]}
    events = [
        {**e, **r[f"/case/timeline/events/{e['event_id']}{q}"]["data"], "category_name": e["category_name"]}
        for e in r[f"/case/timeline/events/list{q}"]["data"]["timeline"]
    ]
    return {
        "directories": directories, "notes": notes, "events": events,
        "assets": r[f"/case/assets/list{q}"]["data"]["assets"],
        "iocs": r[f"/case/ioc/list{q}"]["data"]["ioc"],
    }


@pytest.fixture
def phishing():
    return build_case(_case(2), _children(2), load_mapping(), UTC_TZ, IRIS_URL)


def test_reference_dates_and_title(phishing):
    inc = phishing.incident
    assert inc.incident_ref == "INC-2025-482913"
    assert inc.opened_at == datetime(2025, 3, 3, tzinfo=UTC)
    assert inc.closed_at == datetime(2025, 3, 7, tzinfo=UTC)
    assert inc.title == "Phishing - finance mailbox compromise"  # IRIS "#2 - " prefix dropped


def test_enums_are_mapped(phishing):
    inc = phishing.incident
    assert (inc.severity, inc.disposition, inc.source) == ("high", "tp_remediated", "other")


def test_external_ref_and_metadata(phishing):
    inc = phishing.incident
    assert inc.external_ref == "2"
    assert inc.external_url == "https://iris.test/case?cid=2"
    assert inc.metadata["iris_classification"] == "fraud:phishing"
    assert inc.metadata["iris_customer"] == "IrisInitialClient"
    assert inc.metadata["imported_from"] == "dfir_iris"


def test_summary_is_converted_to_html(phishing):
    summary = phishing.incident.executive_summary
    assert summary.startswith("<h1>Executive summary</h1>")
    assert "<strong>finance</strong>" in summary
    assert "the ticket (https://servicedesk.local/482913)" in summary


def test_notes_have_every_note_in_directory_order_plus_closing_note(phishing):
    notes = phishing.incident.notes
    # By directory path, so a directory's own notes come before its subdirectories'.
    headings = [
        "Containment / Actions",
        "Investigation / Triage",
        "Investigation / Mail analysis / Headers",
        "Closing note",
        "IOCs not imported",
    ]
    positions = [notes.index(f"<h2>{h}</h2>") for h in headings]
    assert positions == sorted(positions)
    assert "IRIS note by administrator" in notes
    assert "SPF <em>fail</em>." in notes
    assert "Closed after password reset and block." in notes
    assert "<li>mutex: SuspiciousMutex42 - unmapped type</li>" in notes


def test_timeline_uses_iris_utc_times_in_order(phishing):
    times = [t.occurred_at for t in phishing.timeline]
    assert times == sorted(times)
    first, last = phishing.timeline[0], phishing.timeline[-1]
    # Entered as 08:12:45 +01:00 and 09:00 -05:00 in IRIS.
    assert first.occurred_at == datetime(2025, 3, 3, 7, 12, 45, tzinfo=UTC)
    assert last.occurred_at == datetime(2025, 3, 4, 14, 0, tzinfo=UTC)
    assert first.entry_type == "detection"  # Initial Access
    assert first.description.startswith("Phishing email received\n\nUser j.doe received")
    assert first.metadata["iris_source"] == "Mail gateway"
    assert first.metadata["iris_tz"] == "+01:00"
    assert first.asset_ids and first.ioc_ids
    assert {t.entry_type for t in phishing.timeline} == {"detection", "analysis", "containment"}


def test_assets(phishing):
    by_name = {a.name: a for a in phishing.assets}
    assert by_name["FIN-WS-042"].asset_type == "workstation"
    assert by_name["FIN-WS-042"].status == "confirmed"
    assert "IP: 10.1.4.42 | Domain: corp.local" in by_name["FIN-WS-042"].description
    assert by_name["j.doe"].asset_type == "account"
    assert by_name["EDGE-FW-01"].asset_type == "network_device"
    assert by_name["EDGE-FW-01"].status == "cleared"
    assert by_name["FIN-WS-042"].tags == ["seed", "test"]


def test_iocs_types_and_tlp(phishing):
    by_value = {i.value: i for i in phishing.iocs}
    assert by_value["login-micros0ft.example"].ioc_type == "domain"
    assert by_value["203.0.113.77"].ioc_type == "ip"
    assert by_value["203.0.113.77"].tlp_level == "amber"  # amber+strict
    assert by_value["44d88612fea8a8f36de82e1278abb02f"].tlp_level == "white"  # clear
    assert by_value["invoice_7731.html"].ioc_type == "file"
    assert by_value["evil@phish.example"].ioc_type == "email"
    assert "SuspiciousMutex42" not in by_value
    assert [u.value for u in phishing.unsupported_iocs] == ["SuspiciousMutex42"]


def test_date_timezone_option_moves_midnight():
    bundle = build_case(_case(2), _children(2), load_mapping(), ZoneInfo("Europe/Bucharest"), IRIS_URL)
    assert bundle.incident.opened_at == datetime(2025, 3, 2, 22, 0, tzinfo=UTC)


def test_case_without_soc_id_is_skipped():
    with pytest.raises(SkipCase) as exc:
        build_case(_case(4), _children(4), load_mapping(), UTC_TZ, IRIS_URL)
    assert exc.value.reason == "missing_soc_id"


def test_open_case_is_skipped():
    with pytest.raises(SkipCase) as exc:
        build_case({**_case(2), "close_date": None}, _children(2), load_mapping(), UTC_TZ, IRIS_URL)
    assert exc.value.reason == "not_closed"


@pytest.mark.parametrize("soc_id, expected", [
    ("482913", "INC-2025-482913"),
    (" 77 ", "INC-2025-0077"),
    ("000123", "INC-2025-0123"),
    (482913, "INC-2025-482913"),
])
def test_build_ref(soc_id, expected):
    assert build_ref(soc_id, datetime(2025, 1, 1, tzinfo=UTC)) == expected


@pytest.mark.parametrize("soc_id, reason", [
    ("", "missing_soc_id"), (None, "missing_soc_id"), ("SOC-12", "invalid_soc_id"),
    ("0", "invalid_soc_id"), ("1" * 30, "invalid_soc_id"),
])
def test_build_ref_rejects(soc_id, reason):
    with pytest.raises(SkipCase) as exc:
        build_ref(soc_id, datetime(2025, 1, 1, tzinfo=UTC))
    assert exc.value.reason == reason


def test_iocs_are_deduplicated_case_insensitively():
    iocs, unsupported = build_iocs([
        {"ioc_id": 1, "ioc_value": "Evil.example", "ioc_type": "domain", "tlp_name": "red", "ioc_tags": "a"},
        {"ioc_id": 2, "ioc_value": "evil.example ", "ioc_type": "hostname", "tlp_name": "green",
         "ioc_tags": "b", "ioc_description": "seen twice"},
        {"ioc_id": 3, "ioc_value": "", "ioc_type": "domain"},
    ], load_mapping())
    assert len(iocs) == 1 and not unsupported
    assert iocs[0].iris_ids == [1, 2]
    assert iocs[0].tags == ["a", "b"]
    assert iocs[0].description == "seen twice"


def test_helpers():
    assert strip_case_prefix("#12 - Name", 12) == "Name"
    assert strip_case_prefix("#1 - Name", 12) == "#1 - Name"
    assert day_start_utc(None, UTC_TZ) is None
