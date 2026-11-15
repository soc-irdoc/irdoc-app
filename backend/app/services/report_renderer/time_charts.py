"""Time spent on an incident, for the report's Time Spent block (#165).

Two different measures, kept apart on purpose:

- Effort: minutes analysts entered on timeline entries (time_spent_minutes).
  Entries without a value are "not tracked" and count for nothing.
- Activity window: for each entry type, the span from its first to its last
  entry's occurred_at. It shows when the work happened, not how long anyone
  worked on it (gaps include nights, waiting and parallel work), so it is never
  added up or presented as effort.

The charts are plain SVG strings, rendered server-side like the graph
snapshot, so WeasyPrint needs no browser or JavaScript.
"""
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from html import escape

TYPE_LABELS = {
    "detection": "Detection",
    "analysis": "Analysis",
    "containment": "Containment",
    "evidence": "Evidence",
    "comms": "Comms",
    "note": "Note",
}
TYPE_COLOURS = {
    "detection": "#dc2626",
    "analysis": "#2563eb",
    "containment": "#d97706",
    "evidence": "#7c3aed",
    "comms": "#059669",
    "note": "#64748b",
}
_FALLBACK_COLOUR = "#94a3b8"
_FONT = "font-family=\"Helvetica, Arial, sans-serif\""


def type_label(entry_type: str) -> str:
    return TYPE_LABELS.get(entry_type, entry_type)


def format_minutes(minutes: int) -> str:
    hours, mins = divmod(int(minutes), 60)
    if hours and mins:
        return f"{hours} h {mins} min"
    if hours:
        return f"{hours} h"
    return f"{mins} min"


# ─── Effort ───────────────────────────────────────────────────────────────────

@dataclass
class EffortRow:
    entry_type: str
    occurred_at: datetime
    description: str
    minutes: int


@dataclass
class EffortSummary:
    rows: list[EffortRow] = field(default_factory=list)
    total_minutes: int = 0
    tracked_entries: int = 0
    by_type: list[tuple[str, int]] = field(default_factory=list)


def effort_summary(entries) -> EffortSummary:
    rows = [
        EffortRow(e.entry_type, e.occurred_at, e.description, e.time_spent_minutes)
        for e in sorted(entries, key=lambda e: e.occurred_at)
        if e.time_spent_minutes is not None
    ]
    totals: dict[str, int] = defaultdict(int)
    for row in rows:
        totals[row.entry_type] += row.minutes
    by_type = sorted(totals.items(), key=lambda kv: (-kv[1], type_label(kv[0])))
    return EffortSummary(
        rows=rows,
        total_minutes=sum(r.minutes for r in rows),
        tracked_entries=len(rows),
        by_type=by_type,
    )


# ─── Activity windows ─────────────────────────────────────────────────────────

@dataclass
class ActivityWindow:
    entry_type: str
    start: datetime
    end: datetime
    count: int
    times: list[datetime] = field(default_factory=list)


def activity_windows(entries) -> list[ActivityWindow]:
    times: dict[str, list[datetime]] = defaultdict(list)
    for e in entries:
        times[e.entry_type].append(e.occurred_at)
    windows = [
        ActivityWindow(t, min(ts), max(ts), len(ts), sorted(ts)) for t, ts in times.items()
    ]
    return sorted(windows, key=lambda w: (w.start, type_label(w.entry_type)))


# ─── SVG: effort by type (donut) ──────────────────────────────────────────────

def render_effort_donut_svg(by_type: list[tuple[str, int]]) -> str | None:
    slices = [(t, m) for t, m in by_type if m > 0]
    total = sum(m for _, m in slices)
    if not total:
        return None

    cx, cy, r_outer, r_inner = 90, 90, 80, 48
    width, height = 420, 180
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="Effort by entry type">'
    ]
    if len(slices) == 1:
        t, _ = slices[0]
        colour = TYPE_COLOURS.get(t, _FALLBACK_COLOUR)
        rm = (r_outer + r_inner) / 2
        parts.append(
            f'<circle class="slice" cx="{cx}" cy="{cy}" r="{rm}" fill="none" '
            f'stroke="{colour}" stroke-width="{r_outer - r_inner}"/>'
        )
    else:
        angle = -math.pi / 2
        for t, m in slices:
            sweep = 2 * math.pi * m / total
            end = angle + sweep
            large = 1 if sweep > math.pi else 0
            p1 = (cx + r_outer * math.cos(angle), cy + r_outer * math.sin(angle))
            p2 = (cx + r_outer * math.cos(end), cy + r_outer * math.sin(end))
            p3 = (cx + r_inner * math.cos(end), cy + r_inner * math.sin(end))
            p4 = (cx + r_inner * math.cos(angle), cy + r_inner * math.sin(angle))
            d = (
                f"M {p1[0]:.2f} {p1[1]:.2f} A {r_outer} {r_outer} 0 {large} 1 {p2[0]:.2f} {p2[1]:.2f} "
                f"L {p3[0]:.2f} {p3[1]:.2f} A {r_inner} {r_inner} 0 {large} 0 {p4[0]:.2f} {p4[1]:.2f} Z"
            )
            colour = TYPE_COLOURS.get(t, _FALLBACK_COLOUR)
            parts.append(f'<path class="slice" d="{d}" fill="{colour}" stroke="#ffffff" stroke-width="1"/>')
            angle = end
    parts.append(
        f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" font-size="12" font-weight="bold" '
        f'{_FONT} fill="#0f172a">{escape(format_minutes(total))}</text>'
    )
    # Legend
    for i, (t, m) in enumerate(slices):
        y = 24 + i * 22
        colour = TYPE_COLOURS.get(t, _FALLBACK_COLOUR)
        pct = round(100 * m / total)
        parts.append(f'<rect x="200" y="{y - 10}" width="12" height="12" rx="2" fill="{colour}"/>')
        parts.append(
            f'<text x="220" y="{y}" font-size="11" {_FONT} fill="#0f172a">'
            f'{escape(type_label(t))}: {escape(format_minutes(m))} ({pct}%)</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


# ─── SVG: activity windows (horizontal timeline) ──────────────────────────────

def render_activity_gantt_svg(
    windows: list[ActivityWindow],
    milestones: list[tuple[str, datetime | None]],
) -> str | None:
    if sum(w.count for w in windows) < 2:
        return None
    marks = [(label, at) for label, at in milestones if at is not None]
    points = [w.start for w in windows] + [w.end for w in windows] + [at for _, at in marks]
    t_min, t_max = min(points), max(points)
    span = (t_max - t_min).total_seconds() or 1.0

    label_w, chart_w, row_h, top = 110, 540, 26, 28
    width = label_w + chart_w + 20
    height = top + row_h * len(windows) + 40

    def x(at: datetime) -> float:
        return label_w + chart_w * (at - t_min).total_seconds() / span

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="Activity window by entry type">'
    ]
    bottom = top + row_h * len(windows)
    # Milestones: vertical dashed lines with labels on top
    for label, at in marks:
        mx = x(at)
        parts.append(
            f'<line x1="{mx:.1f}" y1="{top - 6}" x2="{mx:.1f}" y2="{bottom}" stroke="#94a3b8" '
            f'stroke-width="1" stroke-dasharray="3,3"/>'
        )
        parts.append(
            f'<text x="{mx:.1f}" y="{top - 10}" text-anchor="middle" font-size="9" {_FONT} '
            f'fill="#475569">{escape(label)}</text>'
        )
    for i, w in enumerate(windows):
        y = top + i * row_h
        colour = TYPE_COLOURS.get(w.entry_type, _FALLBACK_COLOUR)
        parts.append(
            f'<text x="{label_w - 8}" y="{y + row_h / 2 + 4:.1f}" text-anchor="end" font-size="11" '
            f'{_FONT} fill="#0f172a">{escape(type_label(w.entry_type))} ({w.count})</text>'
        )
        x1, x2 = x(w.start), x(w.end)
        bar_w = max(x2 - x1, 4.0)
        parts.append(
            f'<rect class="bar" x="{x1:.1f}" y="{y + 6}" width="{bar_w:.1f}" height="{row_h - 12}" '
            f'rx="3" fill="{colour}" fill-opacity="0.35" stroke="{colour}"/>'
        )
        for at in w.times:
            parts.append(f'<circle cx="{x(at):.1f}" cy="{y + row_h / 2:.1f}" r="2.5" fill="{colour}"/>')
    # Axis: start and end times
    parts.append(
        f'<line x1="{label_w}" y1="{bottom + 4}" x2="{label_w + chart_w}" y2="{bottom + 4}" stroke="#cbd5e1"/>'
    )
    fmt = "%Y-%m-%d %H:%M UTC"
    parts.append(
        f'<text x="{label_w}" y="{bottom + 20}" font-size="9" {_FONT} fill="#475569">'
        f'{escape(t_min.strftime(fmt))}</text>'
    )
    parts.append(
        f'<text x="{label_w + chart_w}" y="{bottom + 20}" text-anchor="end" font-size="9" {_FONT} '
        f'fill="#475569">{escape(t_max.strftime(fmt))}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)
