from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class TimelineEntryCreate(BaseModel):
    entry_type: Literal["detection", "analysis", "containment", "evidence", "comms", "note"]
    occurred_at: datetime
    description: str
    source: str = "manual"
    is_pinned: bool = False
    metadata: dict = {}


class TimelineEntryUpdate(BaseModel):
    entry_type: Literal["detection", "analysis", "containment", "evidence", "comms", "note"] | None = None
    occurred_at: datetime | None = None
    description: str | None = None
    source: str | None = None
    is_pinned: bool | None = None
    metadata: dict | None = None


class AttachmentBrief(BaseModel):
    id: UUID
    original_name: str
    mime_type: str | None
    file_size: int | None
    sha256: str

    model_config = {"from_attributes": True}


class TimelineEntryOut(BaseModel):
    id: UUID
    incident_id: UUID
    author_id: UUID | None
    entry_type: str
    occurred_at: datetime
    description: str
    source: str
    is_pinned: bool
    metadata: dict
    created_at: datetime
    updated_at: datetime
    attachments: list[AttachmentBrief] = []

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        if hasattr(obj, "metadata_"):
            obj.__dict__["metadata"] = obj.metadata_
        return super().model_validate(obj, *args, **kwargs)
