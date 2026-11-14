"""Time spent in reports: effort (entered by analysts) and activity windows
(derived from timestamps), kept apart (Refs #165)."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.report_renderer import time_charts as tc

T0 = datetime(2026, 11, 14, 9, 0, tzinfo=timezone.utc)


def _entry(entry_type: str, minutes_after: int, spent: int | None = None, text: str = "x"):
    return SimpleNamespace(
        entry_type=entry_type, occurred_at=T0 + timedelta(minutes=minutes_after),
        time_spent_minutes=spent, description=f"<p>{text}</p>",
    )


ENTRIES = [
    _entry("detection", 0, 10, "Collected email log"),
    _entry("analysis", 15, 20, "Reviewed headers"),
    _entry("analysis", 60, None, "Untracked note"),
    _entry("containment", 120, 0, "Blocked sender"),
    _entry("analysis", 180, 20, "Queried SIEM"),
]


def test_effort_counts_only_tracked_entries():
    effort = tc.effort_summary(ENTRIES)
    assert effort.total_minutes == 50
    assert effort.tracked_entries == 4  # the 0-minute entry is tracked; the None one isn't
    assert [(r.entry_type, r.minutes) for r in effort.rows] == [
        ("detection", 10), ("analysis", 20), ("containment", 0), ("analysis", 20),
    ]
    assert effort.by_type == [("analysis", 40), ("detection", 10), ("containment", 0)]


def test_effort_is_empty_when_nothing_was_tracked():
    effort = tc.effort_summary([_entry("note", 0)])
    assert effort.total_minutes == 0 and effort.rows == [] and effort.by_type == []


def test_activity_windows_span_first_to_last_entry_of_each_type():
    windows = tc.activity_windows(ENTRIES)
    by_type = {w.entry_type: w for w in windows}
    assert by_type["analysis"].start == T0 + timedelta(minutes=15)
    assert by_type["analysis"].end == T0 + timedelta(minutes=180)
    assert by_type["analysis"].count == 3
    assert by_type["detection"].start == by_type["detection"].end  # a single entry
    assert [w.entry_type for w in windows] == ["detection", "analysis", "containment"]  # by start


def test_format_minutes():
    assert tc.format_minutes(0) == "0 min"
    assert tc.format_minutes(45) == "45 min"
    assert tc.format_minutes(60) == "1 h"
    assert tc.format_minutes(135) == "2 h 15 min"


def test_donut_svg_has_one_slice_per_type_and_escapes_text():
    svg = tc.render_effort_donut_svg([("analysis", 40), ("detection", 10), ("containment", 0)])
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    assert svg.count('class="slice"') == 2  # 0-minute types get no slice
    assert "Analysis" in svg and "40 min" in svg
    assert tc.render_effort_donut_svg([]) is None
    assert tc.render_effort_donut_svg([("note", 0)]) is None


def test_single_type_donut_is_a_full_ring():
    svg = tc.render_effort_donut_svg([("analysis", 30)])
    assert "<circle" in svg and 'class="slice"' in svg


def test_gantt_svg_has_a_bar_per_type_and_milestones():
    milestones = [("Opened", T0 - timedelta(minutes=5)), ("Contained", T0 + timedelta(minutes=130)), ("Closed", None)]
    svg = tc.render_activity_gantt_svg(tc.activity_windows(ENTRIES), milestones)
    assert svg.count('class="bar"') == 3
    assert "Opened" in svg and "Contained" in svg and "Closed" not in svg
    assert "Detection" in svg and "Containment" in svg


def test_gantt_needs_two_entries():
    assert tc.render_activity_gantt_svg(tc.activity_windows([_entry("note", 0)]), []) is None


def test_gantt_escapes_unexpected_entry_types():
    windows = tc.activity_windows([_entry("<script>", 0), _entry("<script>", 30)])
    svg = tc.render_activity_gantt_svg(windows, [])
    assert "<script>" not in svg and "&lt;script&gt;" in svg
