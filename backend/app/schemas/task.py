from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    phase: str | None = None
    priority: Literal["critical", "high", "medium", "low"] = "medium"
    assigned_to: str | None = None
    sort_order: int = 0


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    phase: str | None = None
    priority: Literal["critical", "high", "medium", "low"] | None = None
    status: Literal["pending", "in_progress", "done", "skipped"] | None = None
    assigned_to: str | None = None
    sort_order: int | None = None


class TaskOut(BaseModel):
    id: UUID
    incident_id: UUID
    template_id: UUID | None
    title: str
    description: str | None
    phase: str | None
    priority: str
    status: str
    assigned_to: UUID | None
    completed_at: datetime | None
    completed_by: UUID | None
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}
