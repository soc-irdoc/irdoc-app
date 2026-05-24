"""Unit tests for fixed report section has_data() checks."""
import pytest
from unittest.mock import MagicMock
from app.services.report_renderer.fixed_report import _FIXED_SECTIONS


def _make_payload(**overrides):
    """Build a minimal mock ReportPayload."""
    p = MagicMock()
    p.entries = []
    p.iocs = []
    p.tasks = []
    p.attachments = []
    p.ai_executive_summary = None
    p.incident.executive_summary = None
    for k, v in overrides.items():
        setattr(p, k, v)
    return p


def _section(type_):
    return next(s for s in _FIXED_SECTIONS if s["type"] == type_)


def test_cover_always_shown():
    p = _make_payload()
    assert _section("cover")["has_data"](p) is True


def test_stat_row_always_shown():
    p = _make_payload()
    assert _section("stat_row")["has_data"](p) is True


def test_executive_summary_hidden_when_empty():
    p = _make_payload()
    p.incident.executive_summary = None
    assert _section("section")["has_data"](p) is False


def test_executive_summary_shown_when_set():
    p = _make_payload()
    p.incident.executive_summary = "This is the exec summary."
    assert _section("section")["has_data"](p) is True


def test_timeline_hidden_when_no_entries():
    p = _make_payload(entries=[])
    assert _section("timeline")["has_data"](p) is False


def test_timeline_shown_with_entries():
    p = _make_payload(entries=[MagicMock()])
    assert _section("timeline")["has_data"](p) is True


def test_ioc_table_hidden_when_no_iocs():
    p = _make_payload(iocs=[])
    assert _section("ioc_table")["has_data"](p) is False


def test_ioc_table_shown_with_iocs():
    p = _make_payload(iocs=[MagicMock()])
    assert _section("ioc_table")["has_data"](p) is True


def test_task_list_hidden_when_no_tasks():
    p = _make_payload(tasks=[])
    assert _section("task_list")["has_data"](p) is False


def test_evidence_register_hidden_when_no_attachments():
    p = _make_payload(attachments=[])
    assert _section("evidence_register")["has_data"](p) is False


def test_ai_narrative_hidden_when_no_summary():
    p = _make_payload()
    p.ai_executive_summary = None
    assert _section("text_block")["has_data"](p) is False


def test_ai_narrative_shown_when_summary_present():
    p = _make_payload()
    p.ai_executive_summary = "AI generated text."
    assert _section("text_block")["has_data"](p) is True
