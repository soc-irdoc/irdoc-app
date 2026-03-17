"""
Investigation graph API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.models.user import User
from app.services import graph_service

router = APIRouter(tags=["graph"])


class AddEdgeRequest(BaseModel):
    source_node_id: str
    target_node_id: str
    label: str | None = None


@router.get("/incidents/{incident_id}/graph")
async def get_graph(
    incident_id: str,
    current_user: User = Depends(require_permission("incidents.read")),
    db: AsyncSession = Depends(get_db),
):
    """Return the full investigation graph (nodes + edges) for an incident."""
    graph = await graph_service.build_graph(incident_id, db)
    return {
        "data": graph,
        "meta": {
            "node_count": len(graph["nodes"]),
            "edge_count": len(graph["edges"]),
        },
        "error": None,
    }


@router.post("/incidents/{incident_id}/graph/edges", status_code=status.HTTP_201_CREATED)
async def add_edge(
    incident_id: str,
    body: AddEdgeRequest,
    current_user: User = Depends(require_permission("timeline.create")),
    db: AsyncSession = Depends(get_db),
):
    """Manually create a relationship edge between two graph nodes."""
    edge = await graph_service.add_manual_edge(
        incident_id=incident_id,
        source_node_id=body.source_node_id,
        target_node_id=body.target_node_id,
        label=body.label,
        created_by=str(current_user.id),
        db=db,
    )
    return {
        "data": {
            "id": f"manual-{edge.id}",
            "source": edge.source_node_id,
            "target": edge.target_node_id,
            "label": edge.label,
        },
        "meta": {},
        "error": None,
    }


@router.delete("/incidents/{incident_id}/graph/edges/{edge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_edge(
    incident_id: str,
    edge_id: str,
    current_user: User = Depends(require_permission("timeline.create")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a manually created graph edge."""
    # edge_id from frontend is "manual-{uuid}" — strip prefix
    raw_id = edge_id.replace("manual-", "", 1)
    deleted = await graph_service.delete_manual_edge(raw_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Edge not found")
