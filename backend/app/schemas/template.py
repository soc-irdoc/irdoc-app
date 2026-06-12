from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class IncidentTemplateCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    tasks_json: list = []


class IncidentTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    tasks_json: list | None = None
    is_hidden: bool | None = None


class IncidentTemplateOut(BaseModel):
    id: UUID
    org_id: UUID | None
    name: str
    slug: str
    description: str | None
    is_system: bool
    is_hidden: bool
    tasks_json: list
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportTemplateCreate(BaseModel):
    name: str
    destination: str = "custom"
    description: str | None = None
    schema_json: list = []


class ReportTemplateUpdate(BaseModel):
    name: str | None = None
    destination: str | None = None
    description: str | None = None
    schema_json: list | None = None
    primary_colour: str | None = None
    company_name: str | None = None
    ai_auto_generate: bool | None = None
    is_hidden: bool | None = None


class ReportTemplateOut(BaseModel):
    id: UUID
    org_id: UUID | None
    name: str
    destination: str
    description: str | None
    is_system: bool
    is_default: bool
    ai_auto_generate: bool
    is_hidden: bool
    schema_json: list
    logo_data_uri: str | None
    primary_colour: str | None
    company_name: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
