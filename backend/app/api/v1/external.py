"""
Inbound webhook API — authenticated via API key (not JWT).
Any tool that can POST JSON can create IRDoc cases.
Rate limited: WEBHOOK_RATE_LIMIT requests/min per key.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import require_scope
from app.schemas.external import ExternalIncidentCreate, ExternalIncidentResponse
from app.services import external_service

router = APIRouter(prefix="/external", tags=["external"])


@router.post("/incidents", response_model=ExternalIncidentResponse, status_code=201)
async def create_incident_from_external(
    payload: ExternalIncidentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key=Depends(require_scope("incidents:create")),
):
    """
    Create an incident from an external service desk tool (SDP, Jira, ManageEngine, etc.).
    Authenticated via: Authorization: ApiKey irp_key_xxxxx
    """
    # Enforce payload size limit
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.WEBHOOK_MAX_PAYLOAD_BYTES:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Payload exceeds {settings.WEBHOOK_MAX_PAYLOAD_BYTES} bytes",
        )

    incident = await external_service.create_from_webhook(
        db,
        org_id=str(api_key.org_id),
        payload=payload,
        api_key_id=str(api_key.id),
    )

    return ExternalIncidentResponse(
        incident_id=str(incident.id),
        incident_ref=incident.incident_ref,
        external_ref=payload.external_ref,
        workspace_url=f"{settings.BASE_URL}/incidents/{incident.id}",
    )
