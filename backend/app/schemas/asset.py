from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ASSET_TYPES = Literal[
    "host",
    "server",
    "workstation",
    "laptop",
    "mobile",
    "network_device",
    "account",
    "service_account",
    "file",
    "directory",
    "url",
    "email_address",
    "database",
    "application",
    "cloud_resource",
    "other",
]

ASSET_STATUSES = Literal["suspected", "confirmed", "remediated", "cleared"]
ASSET_CRITICALITIES = Literal["critical", "high", "medium", "low"]


class AssetCreate(BaseModel):
    asset_type: ASSET_TYPES
    name: str
    description: str | None = None
    status: ASSET_STATUSES = "suspected"
    criticality: ASSET_CRITICALITIES = "medium"
    tags: list[str] = []
    metadata: dict = {}


class AssetBulkCreate(BaseModel):
    """Create multiple assets at once (one per line in UI)."""
    asset_type: ASSET_TYPES
    names: list[str]
    description: str | None = None
    status: ASSET_STATUSES = "suspected"
    criticality: ASSET_CRITICALITIES = "medium"
    tags: list[str] = []


class AssetUpdate(BaseModel):
    asset_type: ASSET_TYPES | None = None
    name: str | None = None
    description: str | None = None
    status: ASSET_STATUSES | None = None
    criticality: ASSET_CRITICALITIES | None = None
    tags: list[str] | None = None
    metadata: dict | None = None


class AssetOut(BaseModel):
    id: UUID
    incident_id: UUID
    asset_type: str
    name: str
    description: str | None
    status: str
    criticality: str
    tags: list[str]
    metadata: dict
    added_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        if hasattr(obj, "metadata_"):
            obj.__dict__["metadata"] = obj.metadata_
        return super().model_validate(obj, *args, **kwargs)


class AssetLinkCreate(BaseModel):
    source_id: UUID
    target_id: UUID
    link_type: Literal[
        "communicates_with",
        "owns",
        "runs",
        "connects_to",
        "authenticates_to",
        "contains",
        "accesses",
        "lateral_movement",
        "exfiltration_target",
        "related",
    ]
    label: str | None = None


class AssetLinkOut(BaseModel):
    id: UUID
    incident_id: UUID
    source_id: UUID
    target_id: UUID
    link_type: str
    label: str | None
    created_by: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AssetTimelineLinkCreate(BaseModel):
    asset_ids: list[UUID]
    timeline_entry_id: UUID
