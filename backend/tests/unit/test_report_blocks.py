"""Render tests for field-bound and configurable report block partials."""
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services.report_renderer.engine import _build_jinja_env
from app.services.report_renderer.fields import SUMMARY_FIELDS

_env = _build_jinja_env()


def _payload(**incident_fields):
    incident = SimpleNamespace(
        executive_summary=None,
        notes=None,
        lessons_learned=None,
        actions_todo=None,
        attack_vector=[],
        metadata_={},
    )
    for k, v in incident_fields.items():
        setattr(incident, k, v)
    return SimpleNamespace(
        incident=incident,
        attachments=[],
        uploader_names={},
        ai_executive_summary=None,
        ai_recommendations=None,
    )


def _render(block, p):
    tpl = _env.get_template(f"reports/blocks/{block['type']}.html")
    return tpl.render(block=block, p=p, brand={})


@pytest.mark.parametrize("path,column", list(SUMMARY_FIELDS.items()))
def test_section_renders_each_summary_field(path, column):
    p = _payload(**{column: f"<p>content of {column}</p>"})
    html = _render({"type": "section", "label": "X", "field": path}, p)
    assert f"content of {column}" in html
    assert "No data available" not in html


def test_section_legacy_metadata_notes_reads_notes_column():
    p = _payload(notes="<p>real notes</p>", metadata_={})
    html = _render({"type": "section", "field": "incident.metadata.notes"}, p)
    assert "real notes" in html


def test_section_unsupported_field_shows_notice():
    p = _payload()
    html = _render({"type": "section", "field": "incident.metadata.root_cause"}, p)
    assert "no longer supported" in html


def test_section_empty_field_shows_no_data():
    html = _render({"type": "section", "field": "incident.lessons_learned"}, _payload())
    assert "No data available" in html


def test_section_ai_recommendations_legacy_path():
    p = _payload()
    p.ai_recommendations = "<p>patch the VPN</p>"
    html = _render({"type": "section", "field": "ai.recommendations"}, p)
    assert "patch the VPN" in html


def test_text_block_renders_authored_content_sanitized():
    block = {"type": "text_block", "label": "Disclaimer",
             "content": "<p>Privileged</p><script>alert(1)</script>"}
    html = _render(block, _payload())
    assert "<p>Privileged</p>" in html
    assert "<script>" not in html


def test_text_block_legacy_field_still_renders():
    p = _payload(executive_summary="<p>legacy summary</p>")
    html = _render({"type": "text_block", "field": "incident.executive_summary"}, p)
    assert "legacy summary" in html


def _attachment(uploaded_by=None):
    return SimpleNamespace(
        original_name="dump.pcap", mime_type="application/vnd.tcpdump.pcap",
        file_size=2048, sha256="a" * 64, uploaded_by=uploaded_by,
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )


def test_evidence_register_hides_sha256_when_disabled():
    p = _payload()
    p.attachments = [_attachment()]
    html = _render({"type": "evidence_register", "show_sha256": False}, p)
    assert "SHA-256" not in html
    assert "dump.pcap" in html


def test_evidence_register_shows_uploader_when_enabled():
    uid = uuid.uuid4()
    p = _payload()
    p.attachments = [_attachment(uploaded_by=uid)]
    p.uploader_names = {str(uid): "Dana Analyst"}
    html = _render({"type": "evidence_register", "show_uploader": True}, p)
    assert "Uploaded by" in html
    assert "Dana Analyst" in html


def test_evidence_register_uploader_hidden_by_default():
    p = _payload()
    p.attachments = [_attachment(uploaded_by=uuid.uuid4())]
    html = _render({"type": "evidence_register"}, p)
    assert "Uploaded by" not in html
