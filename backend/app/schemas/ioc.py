from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class IOCCreate(BaseModel):
    ioc_type: Literal["email", "domain", "ip", "url", "hash", "file", "username"]
    value: str
    description: str | None = None
    confidence: int = 50
    status: Literal["active", "blocked", "remediated", "fp"] = "active"
    tlp_level: Literal["red", "amber", "green", "white"] = "red"
    tags: list[str] = []


class IOCUpdate(BaseModel):
    description: str | None = None
    confidence: int | None = None
    status: Literal["active", "blocked", "remediated", "fp"] | None = None
    tlp_level: Literal["red", "amber", "green", "white"] | None = None
    tags: list[str] | None = None


class IOCBulkImport(BaseModel):
    """Paste raw text — server auto-detects IOC types."""
    text: str


class IOCOut(BaseModel):
    id: UUID
    incident_id: UUID
    ioc_type: str
    value: str
    description: str | None
    confidence: int
    status: str
    first_seen: datetime
    added_by: UUID | None
    enrichment: dict
    tlp_level: str
    tags: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class IOCDetected(BaseModel):
    """Auto-detected IOC suggestion — not yet saved."""
    ioc_type: str
    value: str
