"""
Field resolution for field-bound report blocks (section, legacy text_block).

The Section block may only bind to the rich-text fields on the incident's
Summary tab. Keep SUMMARY_FIELDS in sync with SECTION_FIELD_OPTIONS in
frontend/src/components/reports/BlockConfigPanel.tsx.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.report_renderer.payload import ReportPayload

# Field path -> Incident column written by the Summary tab.
SUMMARY_FIELDS: dict[str, str] = {
    "incident.executive_summary": "executive_summary",
    "incident.notes": "notes",
    "incident.lessons_learned": "lessons_learned",
    "incident.actions_todo": "actions_todo",
}

# Paths saved by older templates that still resolve to real data.
_LEGACY_ALIASES: dict[str, str] = {
    # Summary tab Notes were always stored in the column, never in metadata.
    "incident.metadata.notes": "incident.notes",
}


def _resolve_legacy(p: "ReportPayload", path: str) -> Any:
    if path == "incident.attack_vector":
        return p.incident.attack_vector or []
    if path == "ai.executive_summary":
        return p.ai_executive_summary
    if path == "ai.recommendations":
        return p.ai_recommendations
    raise KeyError(path)


def is_supported_field(path: str) -> bool:
    path = _LEGACY_ALIASES.get(path, path)
    if path in SUMMARY_FIELDS:
        return True
    return path in {"incident.attack_vector", "ai.executive_summary", "ai.recommendations"}


def resolve_field(p: "ReportPayload", path: str) -> Any:
    """Return the value for a field path, or None if the path is unsupported."""
    path = _LEGACY_ALIASES.get(path, path)
    if path in SUMMARY_FIELDS:
        return getattr(p.incident, SUMMARY_FIELDS[path])
    try:
        return _resolve_legacy(p, path)
    except KeyError:
        return None
