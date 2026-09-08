"""
Investigation graph service.
Builds a nodes + edges graph from incident data (IOCs, timeline entries, IOC-timeline links)
and computes a spring layout using networkx.
"""
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetLink, AssetTimelineLink
from app.models.attachment import Attachment
from app.models.graph import GraphEdge
from app.models.ioc import IOC, IOCTimelineLink
from app.models.timeline import TimelineEntry

logger = logging.getLogger(__name__)

# Node type → color mapping (mirrors frontend status color system)
_IOC_COLORS = {
    "active": "#ef4444",      # red
    "blocked": "#f97316",     # orange
    "remediated": "#22c55e",  # green
    "fp": "#6b7280",          # grey
}
_ENTRY_TYPE_COLORS = {
    "detection": "#ef4444",
    "analysis": "#3b82f6",
    "containment": "#f97316",
    "evidence": "#8b5cf6",
    "comms": "#06b6d4",
    "note": "#6b7280",
}
_EVIDENCE_COLOR = "#8b5cf6"
_ASSET_STATUS_COLORS = {
    "suspected": "#f97316",   # orange
    "confirmed": "#ef4444",   # red
    "remediated": "#22c55e",  # green
    "cleared": "#6b7280",     # grey
}


async def build_graph(incident_id: str, db: AsyncSession) -> dict[str, Any]:
    """
    Build the full graph for an incident.
    Returns { nodes: [...], edges: [...] } ready for React Flow.
    """
    nodes: list[dict] = []
    edges: list[dict] = []
    node_ids: set[str] = set()

    # ── IOC nodes ────────────────────────────────────────────────────────────
    ioc_result = await db.execute(
        select(IOC).where(IOC.incident_id == incident_id)
    )
    iocs = ioc_result.scalars().all()
    ioc_node_map: dict[str, str] = {}  # ioc.id → node_id

    for ioc in iocs:
        node_id = f"ioc-{ioc.id}"
        ioc_node_map[str(ioc.id)] = node_id
        node_ids.add(node_id)
        nodes.append({
            "id": node_id,
            "type": f"ioc_{ioc.ioc_type}",
            "data": {
                "label": ioc.value[:60],
                "ioc_type": ioc.ioc_type,
                "status": ioc.status,
                "confidence": ioc.confidence,
                "tlp": ioc.tlp_level,
                "enrichment": ioc.enrichment or {},
            },
            "position": {"x": 0, "y": 0},  # layout computed below
            "style": {"borderColor": _IOC_COLORS.get(ioc.status, "#ef4444")},
        })

    # ── Timeline entry nodes (pinned + detection types only — avoid graph clutter) ─
    entry_result = await db.execute(
        select(TimelineEntry).where(
            TimelineEntry.incident_id == incident_id
        ).order_by(TimelineEntry.occurred_at)
    )
    entries = entry_result.scalars().all()
    entry_node_map: dict[str, str] = {}

    for entry in entries:
        # Only include pinned entries + detection/containment entries in graph
        if not (entry.is_pinned or entry.entry_type in ("detection", "containment", "evidence")):
            continue
        node_id = f"entry-{entry.id}"
        entry_node_map[str(entry.id)] = node_id
        node_ids.add(node_id)
        nodes.append({
            "id": node_id,
            "type": "event",
            "data": {
                "label": entry.description[:80],
                "entry_type": entry.entry_type,
                "occurred_at": entry.occurred_at.isoformat() if entry.occurred_at else None,
                "is_pinned": entry.is_pinned,
                "source": entry.source,
            },
            "position": {"x": 0, "y": 0},
            "style": {"borderColor": _ENTRY_TYPE_COLORS.get(entry.entry_type, "#6b7280")},
        })

    # ── Evidence nodes (attachments) ─────────────────────────────────────────
    att_result = await db.execute(
        select(Attachment).where(Attachment.incident_id == incident_id).limit(20)
    )
    attachments = att_result.scalars().all()

    for att in attachments:
        if not att.timeline_entry_id:
            continue
        node_id = f"evidence-{att.id}"
        node_ids.add(node_id)
        nodes.append({
            "id": node_id,
            "type": "evidence",
            "data": {
                "label": att.original_name[:60],
                "mime_type": att.mime_type,
                "sha256": att.sha256[:16] + "...",
                "timeline_entry_id": str(att.timeline_entry_id),
            },
            "position": {"x": 0, "y": 0},
            "style": {"borderColor": _EVIDENCE_COLOR},
        })
        # Edge: evidence → entry
        entry_nid = entry_node_map.get(str(att.timeline_entry_id))
        if entry_nid:
            edges.append({
                "id": f"e-att-{att.id}",
                "source": node_id,
                "target": entry_nid,
                "label": "attached to",
                "animated": False,
            })

    # ── Auto-edges: IOC → timeline entry (via ioc_timeline_links) ────────────
    link_result = await db.execute(
        select(IOCTimelineLink).where(
            IOCTimelineLink.ioc_id.in_([ioc.id for ioc in iocs])
        )
    )
    links = link_result.scalars().all()

    for link in links:
        ioc_nid = ioc_node_map.get(str(link.ioc_id))
        entry_nid = entry_node_map.get(str(link.timeline_entry_id))
        if ioc_nid and entry_nid:
            edges.append({
                "id": f"e-link-{link.ioc_id}-{link.timeline_entry_id}",
                "source": ioc_nid,
                "target": entry_nid,
                "label": "mentioned in",
                "animated": True,
            })

    # ── Asset nodes ──────────────────────────────────────────────────────────
    asset_result = await db.execute(
        select(Asset).where(Asset.incident_id == incident_id)
    )
    assets = asset_result.scalars().all()
    asset_node_map: dict[str, str] = {}  # asset.id → node_id

    for asset in assets:
        node_id = f"asset-{asset.id}"
        asset_node_map[str(asset.id)] = node_id
        node_ids.add(node_id)
        nodes.append({
            "id": node_id,
            "type": f"asset_{asset.asset_type}",
            "data": {
                "label": asset.name[:60],
                "asset_type": asset.asset_type,
                "status": asset.status,
                "criticality": asset.criticality,
                "tags": asset.tags or [],
            },
            "position": {"x": 0, "y": 0},
            "style": {"borderColor": _ASSET_STATUS_COLORS.get(asset.status, "#f97316")},
        })

    # ── Asset-to-asset link edges ─────────────────────────────────────────────
    if assets:
        asset_link_result = await db.execute(
            select(AssetLink).where(AssetLink.incident_id == incident_id)
        )
        asset_links = asset_link_result.scalars().all()
        for al in asset_links:
            src_nid = asset_node_map.get(str(al.source_id))
            tgt_nid = asset_node_map.get(str(al.target_id))
            if src_nid and tgt_nid:
                edges.append({
                    "id": f"asset-link-{al.id}",
                    "source": src_nid,
                    "target": tgt_nid,
                    "label": al.label or al.link_type.replace("_", " "),
                    "animated": False,
                })

    # ── Asset-timeline entry edges ────────────────────────────────────────────
    if assets:
        atl_result = await db.execute(
            select(AssetTimelineLink).where(
                AssetTimelineLink.asset_id.in_([a.id for a in assets])
            )
        )
        atl_links = atl_result.scalars().all()
        for atl in atl_links:
            asset_nid = asset_node_map.get(str(atl.asset_id))
            entry_nid = entry_node_map.get(str(atl.timeline_entry_id))
            if asset_nid and entry_nid:
                edges.append({
                    "id": f"asset-entry-{atl.asset_id}-{atl.timeline_entry_id}",
                    "source": asset_nid,
                    "target": entry_nid,
                    "label": "involved in",
                    "animated": False,
                })

    # ── Manual edges (from graph_edges table) ────────────────────────────────
    manual_result = await db.execute(
        select(GraphEdge).where(GraphEdge.incident_id == incident_id)
    )
    manual_edges = manual_result.scalars().all()

    for me in manual_edges:
        edges.append({
            "id": f"manual-{me.id}",
            "source": me.source_node_id,
            "target": me.target_node_id,
            "label": me.label or "",
            "animated": False,
            "data": {"manual": True, "edge_id": str(me.id)},
        })

    # ── Layout computation (spring layout via networkx) ───────────────────────
    nodes = _apply_layout(nodes, edges)

    return {"nodes": nodes, "edges": edges}


def _apply_layout(nodes: list[dict], edges: list[dict]) -> list[dict]:
    """Compute a spring layout using networkx. Falls back to grid if networkx unavailable."""
    if not nodes:
        return nodes
    try:
        import networkx as nx

        graph = nx.DiGraph()
        for node in nodes:
            graph.add_node(node["id"])
        for edge in edges:
            if edge["source"] in graph and edge["target"] in graph:
                graph.add_edge(edge["source"], edge["target"])

        pos = nx.spring_layout(graph, k=300, iterations=50, seed=42, scale=500)

        for node in nodes:
            if node["id"] in pos:
                x, y = pos[node["id"]]
                node["position"] = {"x": round(float(x)), "y": round(float(y))}
        return nodes

    except ImportError:
        logger.warning("networkx not available — using grid layout")
        return _grid_layout(nodes)


def _grid_layout(nodes: list[dict]) -> list[dict]:
    """Simple grid fallback if networkx is unavailable."""
    cols = max(1, int(len(nodes) ** 0.5))
    for i, node in enumerate(nodes):
        node["position"] = {"x": (i % cols) * 200, "y": (i // cols) * 120}
    return nodes


async def add_manual_edge(
    incident_id: str,
    source_node_id: str,
    target_node_id: str,
    label: str | None,
    created_by: str,
    db: AsyncSession,
) -> GraphEdge:
    edge = GraphEdge(
        incident_id=incident_id,
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        label=label,
        created_by=created_by,
    )
    db.add(edge)
    await db.commit()
    await db.refresh(edge)
    return edge


async def delete_manual_edge(edge_id: str, db: AsyncSession) -> bool:
    result = await db.execute(select(GraphEdge).where(GraphEdge.id == edge_id))
    edge = result.scalar_one_or_none()
    if not edge:
        return False
    await db.delete(edge)
    await db.commit()
    return True
