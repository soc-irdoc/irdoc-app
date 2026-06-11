from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


# ─── Report Schemas ──────────────────────────────────────────────────────────

class ReportGenerateRequest(BaseModel):
    report_template_id: str | None = None
    pdf_template_id: str | None = None
    classification: str = "confidential"
    include_ai: bool = False


class ReportOut(BaseModel):
    id: UUID
    incident_id: UUID
    report_template_id: UUID | None
    pdf_template_id: UUID | None
    report_type: str
    format: str = "pdf"
    destination: str | None
    classification: str
    generated_by: UUID | None
    is_ai_assisted: bool
    version_number: int = 1
    status: str
    error_message: str | None
    storage_path: str | None
    sharepoint_url: str | None = None
    generated_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Sync Policy Schemas ─────────────────────────────────────────────────────

class SyncPolicyCreate(BaseModel):
    destination: str
    report_template_id: str | None = None
    trigger_type: str = "on_change"
    debounce_seconds: int = 60
    destination_config: dict = {}


class SyncPolicyUpdate(BaseModel):
    destination: str | None = None
    report_template_id: str | None = None
    trigger_type: str | None = None
    debounce_seconds: int | None = None
    destination_config: dict | None = None
    is_active: bool | None = None


class SyncPolicyOut(BaseModel):
    id: UUID
    incident_id: UUID
    destination: str
    report_template_id: UUID | None
    is_active: bool
    trigger_type: str
    debounce_seconds: int
    last_synced_at: datetime | None
    last_sync_status: str | None
    last_error: str | None
    created_by: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
