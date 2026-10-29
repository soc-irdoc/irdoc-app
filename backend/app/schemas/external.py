from pydantic import BaseModel

from app.core.severity import Severity
from app.schemas.incident import ExternalUrl


class ExternalIncidentCreate(BaseModel):
    """Inbound webhook payload - any tool that can POST JSON can use this."""
    title: str
    severity: Severity = "high"  # sev1-sev4 still accepted
    template: str = "blank"          # matches incident_template.slug
    external_ref: str | None = None  # e.g. "SDP-2026-4421"
    external_source: str | None = None  # e.g. "servicedesk_plus"
    external_url: ExternalUrl = None  # deep-link to original ticket (http/https only)
    description: str | None = None  # pre-populates first timeline entry
    reported_by: str | None = None  # email of original reporter


class ExternalIncidentResponse(BaseModel):
    incident_id: str
    incident_ref: str
    external_ref: str | None
    workspace_url: str
