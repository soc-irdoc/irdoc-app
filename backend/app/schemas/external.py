from typing import Literal

from pydantic import BaseModel


class ExternalIncidentCreate(BaseModel):
    """Inbound webhook payload — any tool that can POST JSON can use this."""
    title: str
    severity: Literal["sev1", "sev2", "sev3", "sev4"] = "sev2"
    template: str = "blank"          # matches incident_template.slug
    external_ref: str | None = None  # e.g. "SDP-2026-4421"
    external_source: str | None = None  # e.g. "servicedesk_plus"
    external_url: str | None = None  # deep-link to original ticket
    description: str | None = None  # pre-populates first timeline entry
    reported_by: str | None = None  # email of original reporter


class ExternalIncidentResponse(BaseModel):
    incident_id: str
    incident_ref: str
    external_ref: str | None
    workspace_url: str
