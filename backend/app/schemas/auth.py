from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: str  # plain str — allows admin@localhost and other local addresses
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class SetupRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    org_name: str = "Default Organization"


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    timezone: str | None = None
    theme: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: UUID
    org_id: UUID | None
    email: str
    full_name: str
    role: str
    avatar_initials: str | None
    timezone: str
    theme: str
    is_active: bool
    must_reset_password: bool

    model_config = {"from_attributes": True}
