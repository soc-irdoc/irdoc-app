from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AttachmentOut(BaseModel):
    id: UUID
    incident_id: UUID
    timeline_entry_id: UUID | None
    original_name: str
    mime_type: str | None
    file_size: int | None
    sha256: str
    storage_backend: str
    is_screenshot: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AttachmentURLResponse(BaseModel):
    url: str
    expires_in: int
