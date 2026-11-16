"""
Pydantic v2 schemas for Phase 5 admin/enterprise endpoints.
"""
import re
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator

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
    name: str | None = Field(None, max_length=200)
    allow_registration: bool | None = None
    invite_only: bool | None = None
    mfa_required: bool | None = None
    # "" clears the logo; otherwise an http(s) URL, stored as a plain string (#167)
    logo_url: str | None = Field(None, max_length=2048)
    accent_color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    # Session timeouts (#123); 0 goes back to the server default.
    session_idle_minutes: int | None = Field(None, ge=0, le=1440)
    session_max_hours: int | None = Field(None, ge=0, le=720)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Organization name can't be empty")
        return v

    @field_validator("logo_url")
    @classmethod
    def logo_url_http_or_empty(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if v == "":
            return ""
        try:
            parsed = AnyHttpUrl(v)
        except ValueError:
            raise ValueError("Logo URL must be an http(s) URL") from None
        if parsed.scheme not in ("http", "https"):
            raise ValueError("Logo URL must be an http(s) URL")
        return v

    @field_validator("session_idle_minutes")
    @classmethod
    def idle_at_least_five_minutes(cls, v: int | None) -> int | None:
        if v is not None and 0 < v < 5:
            raise ValueError("Idle timeout must be at least 5 minutes")
        return v


# ── Storage config ────────────────────────────────────────────────────────────

class StorageConfigOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    backend: str
    is_active: bool
    created_at: datetime
    # config is intentionally omitted - never returned to client


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
    # client_secret is intentionally omitted - never returned to client
    role_mappings: dict[str, Any] = {}
    graph_group_lookup: bool = False
    # The callback URL the backend uses (from BASE_URL), to compare with the
    # App Registration's redirect URI
    redirect_uri: str | None = None


SSORole = Literal["viewer", "analyst", "senior_analyst", "admin"]

# A tenant GUID or a verified domain (contoso.onmicrosoft.com). Both end up in
# login.microsoftonline.com URL paths, so nothing else is let through.
_TENANT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}$")


def _check_tenant(v: str | None) -> str | None:
    if v is None:
        return v
    v = v.strip()
    if v and not _TENANT_RE.match(v):
        raise ValueError("Tenant ID must be a GUID or a domain such as contoso.onmicrosoft.com")
    return v


class SSOConfigUpdate(BaseModel):
    tenant_id: str | None = None
    client_id: str | None = None
    # Required on every save, so no change to SSO can be made without proving
    # knowledge of the secret. Plaintext here; encrypted at the service layer.
    client_secret: str = Field(min_length=1)
    role_mappings: dict[str, SSORole] | None = None
    is_enabled: bool | None = None
    graph_group_lookup: bool | None = None

    @field_validator("client_secret")
    @classmethod
    def _secret_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Re-enter the client secret to save changes")
        return v

    @field_validator("tenant_id")
    @classmethod
    def _tenant_format(cls, v: str | None) -> str | None:
        return _check_tenant(v)


class SSOTestRequest(BaseModel):
    tenant_id: str = Field(min_length=1)
    client_id: str = Field(min_length=1)
    client_secret: str = Field(min_length=1)

    @field_validator("tenant_id")
    @classmethod
    def _tenant_format(cls, v: str) -> str:
        return _check_tenant(v)


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
