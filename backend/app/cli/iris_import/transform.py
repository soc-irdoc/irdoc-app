"""Turn the IRIS API data for one case into plain data ready to insert.

No I/O here: the client fetches, this module converts, the writer inserts.
Everything is a pure function of the IRIS JSON, the mapping and the timezone,
so it is tested without IRIS or a database.

IRIS v2.4.27 facts this relies on (checked against a live instance):
- case open_date / close_date are dates without a time.
- timeline event_date is already UTC; event_date_wtz is the local time and
  event_tz the offset it was entered with.
- case names come back prefixed with "#<case_id> - ".
"""
import html
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from app.cli.iris_import.mapping import Mapping
from app.cli.iris_import.markdown import markdown_to_html
from app.services.incident_service import _sanitize_html, format_ref

EXTERNAL_SOURCE = "dfir_iris"
TIMELINE_SOURCE = "DFIR IRIS"
_REF_MAX_LEN = 30  # incidents.incident_ref is String(30)


class SkipCase(Exception):  # noqa: N818 - a control-flow signal, not an error
    """This case can't be imported; `reason` says why."""

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


@dataclass
class IncidentData:
    incident_ref: str
    title: str
    severity: str
    disposition: str
    source: str
    opened_at: datetime
    closed_at: datetime
    executive_summary: str | None
    notes: str | None
    metadata: dict
    external_ref: str
    external_url: str


@dataclass
class TimelineData:
    iris_id: int
    occurred_at: datetime
    entry_type: str
    description: str
    metadata: dict
    asset_ids: list[int] = field(default_factory=list)
    ioc_ids: list[int] = field(default_factory=list)


@dataclass
class AssetData:
    iris_id: int
    asset_type: str
    name: str
    description: str | None
    status: str
    tags: list[str]
    metadata: dict


@dataclass
class IOCData:
    iris_ids: list[int]
    ioc_type: str
    value: str
    description: str | None
    tlp_level: str
    tags: list[str]


@dataclass
class UnsupportedIOC:
    iris_type: str
    value: str
    description: str | None


@dataclass
class CaseBundle:
    iris_case_id: int
    incident: IncidentData
    timeline: list[TimelineData]
    assets: list[AssetData]
    iocs: list[IOCData]
    unsupported_iocs: list[UnsupportedIOC]


# ── small helpers ────────────────────────────────────────────────────────────

def build_ref(soc_id: object, opened_at: datetime) -> str:
    """INC-<open year>-<SOC ticket ID>, the same format the webhook uses."""
    raw = str(soc_id or "").strip()
    if not raw:
        raise SkipCase("missing_soc_id")
    if not raw.isdigit() or int(raw) == 0:
        raise SkipCase("invalid_soc_id", raw)
    ref = format_ref(opened_at.year, int(raw))
    if len(ref) > _REF_MAX_LEN:
        raise SkipCase("invalid_soc_id", f"{raw} (reference longer than {_REF_MAX_LEN} characters)")
    return ref


def day_start_utc(value: str | None, tz: ZoneInfo) -> datetime | None:
    """Midnight of an IRIS date (YYYY-MM-DD) in `tz`, converted to UTC."""
    if not value:
        return None
    day = date.fromisoformat(str(value)[:10])
    return datetime.combine(day, time.min, tzinfo=tz).astimezone(UTC)


def parse_utc(value: str) -> datetime:
    """An IRIS timestamp without offset, which IRIS stores in UTC."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def strip_case_prefix(name: str, case_id: int) -> str:
    """Drop the "#<id> - " prefix IRIS adds to case names."""
    return re.sub(rf"^\s*#{case_id}\s*-\s*", "", name or "").strip()


def split_tags(value: object) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        names = [t.get("tag_title") or t.get("name") if isinstance(t, dict) else t for t in value]
    else:
        names = str(value).split(",")
    return [str(n).strip() for n in names if n and str(n).strip()]


def _first_author(item: dict) -> str | None:
    history = item.get("modification_history") or {}
    for _, entry in sorted(history.items(), key=lambda kv: float(kv[0])):
        if isinstance(entry, dict) and entry.get("user"):
            return entry["user"]
    return None


def _esc(value: object) -> str:
    return html.escape(str(value), quote=False)


# ── notes ────────────────────────────────────────────────────────────────────

def _directory_paths(directories: list[dict]) -> dict[int, str]:
    """Directory id -> "Parent / Child" path.

    The directories endpoint lists every directory at the top level, with
    each one's children (ids only) under "subdirectories"; parents are
    worked out from those.
    """
    names = {d["id"]: d.get("name") or "" for d in directories}
    parent: dict[int, int] = {}
    for d in directories:
        for sub in d.get("subdirectories") or []:
            parent[sub["id"]] = d["id"]
            names.setdefault(sub["id"], sub.get("name") or "")

    def path(dir_id: int) -> str:
        parts, seen = [], set()
        while dir_id is not None and dir_id not in seen:
            seen.add(dir_id)
            parts.append(names.get(dir_id, ""))
            dir_id = parent.get(dir_id)
        return " / ".join(reversed([p for p in parts if p]))

    return {dir_id: path(dir_id) for dir_id in names}


def build_notes_html(directories: list[dict], notes: dict[int, dict], closing_note: str | None,
                     unsupported_iocs: list[UnsupportedIOC]) -> str | None:
    """All IRIS notes as one HTML document, plus the closing note and unsupported IOCs."""
    paths = _directory_paths(directories)
    ordered: list[tuple[str, dict]] = []
    for d in directories:
        for ref in d.get("notes") or []:
            note = notes.get(ref["id"])
            if note is not None:
                ordered.append((paths.get(d["id"], ""), note))
    # By directory path (a directory's own notes before its subdirectories'), then creation time.
    ordered.sort(key=lambda pn: (pn[0].lower(), pn[1].get("note_creationdate") or "", pn[1].get("note_id", 0)))

    parts: list[str] = []
    for dir_path, note in ordered:
        title = note.get("note_title") or "Untitled note"
        heading = f"{dir_path} / {title}" if dir_path else title
        byline = ["IRIS note"]
        author = _first_author(note)
        if author:
            byline.append(f"by {author}")
        if note.get("note_creationdate"):
            byline.append(f"created {parse_utc(note['note_creationdate']):%Y-%m-%d %H:%M} UTC")
        parts.append(f"<h2>{_esc(heading)}</h2><p><em>{_esc(' '.join(byline))}</em></p>")
        parts.append(markdown_to_html(note.get("note_content")))

    if closing_note and closing_note.strip():
        parts.append("<h2>Closing note</h2>" + markdown_to_html(closing_note))

    if unsupported_iocs:
        items = "".join(
            f"<li>{_esc(i.iris_type)}: {_esc(i.value)}{' - ' + _esc(i.description) if i.description else ''}</li>"
            for i in unsupported_iocs
        )
        parts.append(
            "<h2>IOCs not imported</h2>"
            "<p>These IRIS IOC types have no IRDoc equivalent, so they are kept here instead.</p>"
            f"<ul>{items}</ul>"
        )

    body = "".join(p for p in parts if p)
    return _sanitize_html(body) if body else None


# ── entities ─────────────────────────────────────────────────────────────────

def build_timeline(events: list[dict], mapping: Mapping) -> list[TimelineData]:
    out = []
    for e in events:
        category = e.get("category_name") or "Unspecified"
        text = [e.get("event_title") or "(untitled event)"]
        if (e.get("event_content") or "").strip():
            text.append(e["event_content"].strip())
        if (e.get("event_raw") or "").strip():
            text.append("Raw:\n" + e["event_raw"].strip())
        out.append(TimelineData(
            iris_id=e["event_id"],
            occurred_at=parse_utc(e["event_date"]),
            entry_type=mapping.get("timeline_entry_type", category),
            description="\n\n".join(text),
            metadata={
                "imported_from": EXTERNAL_SOURCE,
                "iris_event_id": e["event_id"],
                "iris_category": category,
                "iris_source": e.get("event_source") or None,
                "iris_local_time": e.get("event_date_wtz"),
                "iris_tz": e.get("event_tz"),
                "iris_tags": split_tags(e.get("event_tags")),
                "iris_in_summary": bool(e.get("event_in_summary")),
                "iris_author": _first_author(e),
            },
            asset_ids=list(e.get("event_assets") or []),
            ioc_ids=list(e.get("event_iocs") or []),
        ))
    out.sort(key=lambda t: (t.occurred_at, t.iris_id))
    return out


def build_assets(assets: list[dict], mapping: Mapping) -> list[AssetData]:
    out = []
    for a in assets:
        details = []
        if a.get("asset_ip"):
            details.append(f"IP: {a['asset_ip']}")
        if a.get("asset_domain"):
            details.append(f"Domain: {a['asset_domain']}")
        description = "\n".join(p for p in [a.get("asset_description") or "", " | ".join(details)] if p)
        out.append(AssetData(
            iris_id=a["asset_id"],
            asset_type=mapping.get("asset_type", a.get("asset_type")),
            name=(a.get("asset_name") or "").strip() or f"IRIS asset {a['asset_id']}",
            description=description or None,
            status=mapping.get("asset_status", a.get("asset_compromise_status_id")),
            tags=split_tags(a.get("asset_tags")),
            metadata={
                "imported_from": EXTERNAL_SOURCE,
                "iris_asset_id": a["asset_id"],
                "iris_asset_type": a.get("asset_type"),
                "ip": a.get("asset_ip") or None,
                "domain": a.get("asset_domain") or None,
                "iris_analysis_status": a.get("analysis_status"),
            },
        ))
    return out


def build_iocs(iocs: list[dict], mapping: Mapping) -> tuple[list[IOCData], list[UnsupportedIOC]]:
    """IRDoc IOCs, deduplicated on (type, value), and the ones with no IRDoc type."""
    merged: dict[tuple[str, str], IOCData] = {}
    unsupported: list[UnsupportedIOC] = []
    for i in iocs:
        value = (i.get("ioc_value") or "").strip()
        if not value:
            continue
        ioc_type = mapping.get("ioc_type", i.get("ioc_type"))
        if ioc_type is None:
            unsupported.append(UnsupportedIOC(i.get("ioc_type") or "(unknown)", value, i.get("ioc_description")))
            continue
        key = (ioc_type, value.lower())
        if key in merged:
            existing = merged[key]
            existing.iris_ids.append(i["ioc_id"])
            existing.tags = sorted(set(existing.tags) | set(split_tags(i.get("ioc_tags"))))
            existing.description = existing.description or i.get("ioc_description") or None
            continue
        merged[key] = IOCData(
            iris_ids=[i["ioc_id"]],
            ioc_type=ioc_type,
            value=value,
            description=i.get("ioc_description") or None,
            tlp_level=mapping.get("tlp", i.get("tlp_name")),
            tags=split_tags(i.get("ioc_tags")),
        )
    return list(merged.values()), unsupported


def build_case(case: dict, children: dict, mapping: Mapping, tz: ZoneInfo, iris_url: str) -> CaseBundle:
    """The full import bundle for one closed IRIS case.

    `case` is one record from /manage/cases/filter. `children` holds the
    case's directories, notes (by id), timeline events (detailed), assets and
    IOCs, as fetched by IrisClient.fetch_children.
    """
    case_id = case["case_id"]
    opened_at = day_start_utc(case.get("open_date"), tz)
    closed_at = day_start_utc(case.get("close_date"), tz)
    if closed_at is None:
        raise SkipCase("not_closed")
    if opened_at is None:
        raise SkipCase("missing_open_date")
    ref = build_ref(case.get("soc_id"), opened_at)

    severity_name = (case.get("severity") or {}).get("severity_name")
    classification = (case.get("classification") or {}).get("name")
    iocs, unsupported = build_iocs(children.get("iocs") or [], mapping)

    incident = IncidentData(
        incident_ref=ref,
        title=strip_case_prefix(case.get("name") or "", case_id) or f"IRIS case {case_id}",
        severity=mapping.get("severity", severity_name),
        disposition=mapping.get("disposition", case.get("status_name")),
        source=mapping.get("source", classification),
        opened_at=opened_at,
        closed_at=closed_at,
        executive_summary=_sanitize_html(markdown_to_html(case.get("description"))) or None,
        notes=build_notes_html(children.get("directories") or [], children.get("notes") or {},
                               case.get("closing_note"), unsupported),
        metadata={
            "imported_from": EXTERNAL_SOURCE,
            "iris_case_id": case_id,
            "iris_case_uuid": case.get("case_uuid"),
            "iris_soc_id": str(case.get("soc_id") or ""),
            "iris_classification": classification,
            "iris_severity": severity_name,
            "iris_outcome": case.get("status_name"),
            "iris_customer": (case.get("client") or {}).get("customer_name"),
            "iris_owner": (case.get("owner") or {}).get("user_name"),
            "iris_opened_by": (case.get("user") or {}).get("user_name"),
            "iris_tags": split_tags(case.get("tags")),
        },
        external_ref=str(case_id),
        external_url=f"{iris_url.rstrip('/')}/case?cid={case_id}",
    )
    return CaseBundle(
        iris_case_id=case_id,
        incident=incident,
        timeline=build_timeline(children.get("events") or [], mapping),
        assets=build_assets(children.get("assets") or [], mapping),
        iocs=iocs,
        unsupported_iocs=unsupported,
    )
