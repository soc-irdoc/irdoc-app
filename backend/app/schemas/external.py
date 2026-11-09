from pydantic import BaseModel, Field, field_validator

from app.core.incident_source import DEFAULT_EXTERNAL_SOURCE, IncidentSource
from app.core.severity import Severity
from app.schemas.incident import ExternalUrl

# incident_ref is String(30); "INC-YYYY-" takes 9 of it.
INCIDENT_NUMBER_MAX_DIGITS = 21


class ExternalIncidentCreate(BaseModel):
    """Inbound webhook payload - any tool that can POST JSON can use this."""
    title: str
    # The source ticket's number, used as the incident's own number:
    # 123456 -> INC-<year>-123456 (#156). Omit to let IRDoc number it.
    incident_number: str | None = Field(
        None, pattern=rf"^[0-9]{{1,{INCIDENT_NUMBER_MAX_DIGITS}}}$",
        description="Digits only; the incident becomes INC-<year>-<number> (padded to 4 digits).",
    )
    severity: Severity = "high"  # sev1-sev4 still accepted
    source: IncidentSource = DEFAULT_EXTERNAL_SOURCE  # what triggered it (#147)
    template: str = "blank"          # matches incident_template.slug
    external_ref: str | None = None  # e.g. "SDP-2026-4421"
    external_source: str | None = None  # e.g. "servicedesk_plus"
    external_url: ExternalUrl = None  # deep-link to original ticket (http/https only)
    description: str | None = None  # pre-populates first timeline entry
    reported_by: str | None = None  # email of original reporter

    @field_validator("incident_number", mode="before")
    @classmethod
    def _number_from_int(cls, v):
        # Ticketing tools often send the number as a JSON number.
        if isinstance(v, int) and not isinstance(v, bool):
            return str(v)
        return v

    @field_validator("incident_number")
    @classmethod
    def _number_not_zero(cls, v: str | None) -> str | None:
        if v is not None and int(v) == 0:
            raise ValueError("incident_number must be greater than 0")
        return v


class ExternalIncidentResponse(BaseModel):
    incident_id: str
    incident_ref: str
    external_ref: str | None
    workspace_url: str
