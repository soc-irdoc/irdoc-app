from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PdfTemplateOut(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    is_default: bool
    file_size: int | None
    mammoth_warnings: list | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PdfTemplateRename(BaseModel):
    name: str
