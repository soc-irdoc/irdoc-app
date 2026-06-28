"""
Pydantic v2 schemas for Phase 5 admin/enterprise endpoints.
"""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, field_validator
import re


# ── User management ───────────────────────────────────────────────────────────

class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    mfa_enabled: bool = False
    auth_provider: str = "local"
    avatar_initials: str | None = None
    created_at: datetime


class UserRoleUpdate(BaseModel):
    role: Literal["admin", "senior_analyst", "analyst", "viewer"]


# ── Invites ───────────────────────────────────────────────────────────────────

class InviteCreate(BaseModel):
    email: str
    role: Literal["admin", "senior_analyst", "analyst", "viewer"] = "analyst"

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+$", v):
            raise ValueError("Invalid email address")
        return v


class InviteOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    email: str
    role: str
    expires_at: datetime
    accepted_at: datetime | None = None
    invited_by_name: str | None = None


class InviteAccept(BaseModel):
    full_name: str
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


# ── Org settings ──────────────────────────────────────────────────────────────

class OrgSettingsUpdate(BaseModel):
    name: str | None = None
    allow_registration: bool | None = None
    invite_only: bool | None = None
    mfa_required: bool | None = None
    logo_url: AnyHttpUrl | None = None
    accent_color: str | None = None


# ── Storage config ────────────────────────────────────────────────────────────

class StorageConfigOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    backend: str
    is_active: bool
    created_at: datetime
    # config is intentionally omitted — never returned to client


class StorageConfigCreate(BaseModel):
    backend: Literal["local", "s3", "azure_blob", "gcs"]
    config: dict[str, Any]


# ── SSO config ────────────────────────────────────────────────────────────────

class SSOConfigOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    org_id: UUID
    is_enabled: bool
    tenant_id: str | None = None
    client_id: str | None = None
    # client_secret is intentionally omitted — never returned to client
    role_mappings: dict[str, Any] = {}


class SSOConfigUpdate(BaseModel):
    tenant_id: str | None = None
    client_id: str | None = None
    client_secret: str | None = None  # plaintext — encrypted at the service layer
    role_mappings: dict[str, Any] | None = None
    is_enabled: bool | None = None


# ── Audit log ─────────────────────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    actor_label: str | None = None
    entity_label: str | None = None
    diff: dict | None = None
    user_id: UUID | None = None
    api_key_id: UUID | None = None
    ip_address: str | None = None
    created_at: datetime

    @field_validator("entity_id", "ip_address", mode="before")
    @classmethod
    def coerce_to_str(cls, v: object) -> str | None:
        if v is None:
            return None
        return str(v)
