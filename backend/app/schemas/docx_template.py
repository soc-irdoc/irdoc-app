from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocxTemplateOut(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    is_default: bool
    file_size: int | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocxTemplateRename(BaseModel):
    name: str
