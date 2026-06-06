"""
Server-side SVG generator for incident investigation graphs.
Converts graph data returned by build_graph() into an SVG string
suitable for inline embedding in WeasyPrint PDF templates.
"""
from __future__ import annotations

import html
from typing import Any

_NODE_W = 160
_NODE_H = 52
_PADDING = 80
_MAX_W = 900
_MAX_H = 680
_MIN_W = 500
_MIN_H = 320

_IOC_STATUS = {
    "active": "#ef4444",
    "blocked": "#f97316",
    "remediated": "#22c55e",
    "fp": "#6b7280",
}
_ASSET_STATUS = {
    "confirmed": "#ef4444",
    "suspected": "#f97316",
    "remediated": "#22c55e",
    "cleared": "#6b7280",
}
_ENTRY_TYPE = {
    "detection": "#ef4444",
    "containment": "#f97316",
    "evidence": "#8b5cf6",
    "analysis": "#3b82f6",
    "comms": "#06b6d4",
    "note": "#94a3b8",
}
_DEFAULT_COLOR = "#cbd5e1"


def _border_color(node: dict) -> str:
    style = node.get("style") or {}
    if isinstance(style, dict) and "borderColor" in style:
        return style["borderColor"]
    data = node.get("data") or {}
    t: str = node.get("type", "")
    if t.startswith("ioc_"):
        return _IOC_STATUS.get(data.get("status", ""), _DEFAULT_COLOR)
    if t.startswith("asset_"):
        return _ASSET_STATUS.get(data.get("status", ""), _DEFAULT_COLOR)
    if t == "event":
        return _ENTRY_TYPE.get(data.get("entry_type", ""), _DEFAULT_COLOR)
    if t == "evidence":
        return "#8b5cf6"
    return _DEFAULT_COLOR


def _trunc(text: str, n: int = 20) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


def _e(text: str) -> str:
    return html.escape(str(text), quote=False)


def render_graph_svg(graph_data: dict[str, Any]) -> str | None:
    """
    Return an SVG string from build_graph() output, or None if the graph is empty.
    The SVG uses a white background and status-coloured node borders — safe to embed
    in a light-background PDF without any browser rendering or theme injection.
    """
    nodes: list[dict] = graph_data.get("nodes", [])
    edges: list[dict] = graph_data.get("edges", [])
    if not nodes:
        return None

    # ── Normalise positions into canvas space ─────────────────────────────────
    raw: dict[str, tuple[float, float]] = {
        n["id"]: (float(n["position"]["x"]), float(n["position"]["y"]))
        for n in nodes
    }
    xs = [p[0] for p in raw.values()]
    ys = [p[1] for p in raw.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)

    cw = max(_MIN_W, min(_MAX_W, int(span_x + _NODE_W + _PADDING * 2)))
    ch = max(_MIN_H, min(_MAX_H, int(span_y + _NODE_H + _PADDING * 2)))

    scale_x = (cw - _PADDING * 2 - _NODE_W) / span_x
    scale_y = (ch - _PADDING * 2 - _NODE_H) / span_y

    def to_canvas(rx: float, ry: float) -> tuple[float, float]:
        return (
            round(_PADDING + (rx - min_x) * scale_x, 1),
            round(_PADDING + (ry - min_y) * scale_y, 1),
        )

    pos: dict[str, tuple[float, float]] = {
        nid: to_canvas(rx, ry) for nid, (rx, ry) in raw.items()
    }

    # ── Assemble SVG ──────────────────────────────────────────────────────────
    out: list[str] = []
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{cw}" height="{ch}" viewBox="0 0 {cw} {ch}">'
    )
    out.append(f'<rect width="{cw}" height="{ch}" fill="#ffffff"/>')

    # Edges drawn first (beneath nodes)
    for edge in edges:
        src, tgt = edge.get("source", ""), edge.get("target", "")
        if src not in pos or tgt not in pos:
            continue
        x1, y1 = pos[src]
        x2, y2 = pos[tgt]
        cx1, cy1 = x1 + _NODE_W / 2, y1 + _NODE_H / 2
        cx2, cy2 = x2 + _NODE_W / 2, y2 + _NODE_H / 2
        dash = "4 3" if edge.get("animated") else "none"
        out.append(
            f'<line x1="{cx1}" y1="{cy1}" x2="{cx2}" y2="{cy2}" '
            f'stroke="#cbd5e1" stroke-width="1.5" stroke-dasharray="{dash}"/>'
        )
        label = str(edge.get("label") or "").strip()
        if label:
            mx = (cx1 + cx2) / 2
            my = (cy1 + cy2) / 2
            lbl = _trunc(label, 16)
            lw = max(len(lbl) * 5 + 8, 40)
            out.append(
                f'<rect x="{mx - lw / 2:.1f}" y="{my - 7:.1f}" '
                f'width="{lw}" height="13" fill="#ffffff" rx="2"/>'
            )
            out.append(
                f'<text x="{mx:.1f}" y="{my + 3:.1f}" '
                f'text-anchor="middle" font-size="8" fill="#94a3b8">{_e(lbl)}</text>'
            )

    # Nodes drawn on top
    for node in nodes:
        nid = node["id"]
        nx_, ny_ = pos[nid]
        color = _border_color(node)
        data = node.get("data") or {}
        label = _trunc(str(data.get("label") or ""), 20)

        subtitle = ""
        if data.get("status"):
            subtitle = str(data["status"])
        elif data.get("entry_type"):
            subtitle = f"[{data['entry_type']}]"
        elif data.get("asset_type"):
            subtitle = str(data["asset_type"]).replace("_", " ")
        elif data.get("mime_type"):
            subtitle = str(data["mime_type"]).split("/")[-1][:14]
        subtitle = _trunc(subtitle, 20)

        out.append(
            f'<rect x="{nx_}" y="{ny_}" width="{_NODE_W}" height="{_NODE_H}" '
            f'rx="8" fill="#f8fafc" stroke="{color}" stroke-width="2"/>'
        )
        label_y = ny_ + (_NODE_H / 2 - 5 if subtitle else _NODE_H / 2 + 4)
        out.append(
            f'<text x="{nx_ + _NODE_W / 2:.1f}" y="{label_y:.1f}" '
            f'text-anchor="middle" font-size="11" font-weight="bold" fill="#0f172a">'
            f"{_e(label)}</text>"
        )
        if subtitle:
            sub_y = ny_ + _NODE_H / 2 + 11
            out.append(
                f'<text x="{nx_ + _NODE_W / 2:.1f}" y="{sub_y:.1f}" '
                f'text-anchor="middle" font-size="9" fill="#64748b">'
                f"{_e(subtitle)}</text>"
            )

    out.append("</svg>")
    return "\n".join(out)
