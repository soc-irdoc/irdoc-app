from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class UserBrief(BaseModel):
    id: UUID
    full_name: str
    email: str
    avatar_initials: str | None

    model_config = {"from_attributes": True}


class ExternalRefOut(BaseModel):
    id: UUID
    external_source: str
    external_ref: str
    external_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ExternalRefCreate(BaseModel):
    external_source: str
    external_ref: str
    external_url: str | None = None


class IncidentCreate(BaseModel):
    title: str
    severity: Literal["sev1", "sev2", "sev3", "sev4"] = "sev2"
    template_id: str | None = None
    assigned_to: str | None = None


class IncidentUpdate(BaseModel):
    title: str | None = None
    severity: Literal["sev1", "sev2", "sev3", "sev4"] | None = None
    status: Literal["open", "contained", "closed", "monitoring"] | None = None
    executive_summary: str | None = None
    attack_vector: list[str] | None = None
    affected_users: int | None = None
    assigned_to: str | None = None
    metadata: dict | None = None


class IncidentOut(BaseModel):
    id: UUID
    org_id: UUID
    incident_ref: str
    title: str
    severity: str
    status: str
    template_id: UUID | None
    assigned_to: UUID | None
    assigned_user: UserBrief | None = None
    created_by: UUID | None
    opened_at: datetime
    contained_at: datetime | None
    closed_at: datetime | None
    executive_summary: str | None
    attack_vector: list[str]
    affected_users: int
    metadata: dict
    created_at: datetime
    updated_at: datetime
    external_refs: list[ExternalRefOut] = []

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        # Map metadata_ ORM column to metadata field
        if hasattr(obj, "metadata_"):
            obj.__dict__["metadata"] = obj.metadata_
        return super().model_validate(obj, *args, **kwargs)


class IncidentStats(BaseModel):
    timeline_count: int
    ioc_count: int
    task_total: int
    task_done: int
    attachment_count: int
    duration_hours: float | None
