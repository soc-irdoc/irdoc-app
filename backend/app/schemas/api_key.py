from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class APIKeyCreate(BaseModel):
    name: str
    scopes: list[str] = []
    expires_at: datetime | None = None


class APIKeyOut(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    scopes: list[str]
    last_used_at: datetime | None
    expires_at: datetime | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class APIKeyCreated(APIKeyOut):
    """Returned only once at creation — contains the full raw key."""
    raw_key: str
