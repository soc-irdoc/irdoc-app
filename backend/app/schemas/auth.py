from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


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
    mfa_enabled: bool
    backup_codes_remaining: int = Field(ge=0, le=10)  # computed from len(backup_codes) on the ORM object

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def compute_backup_codes_remaining(cls, data: object) -> object:
        """Inject backup_codes_remaining before field mapping.

        backup_codes is intentionally NOT a declared field (we never expose the
        hashed codes).  This validator reads the raw list from the ORM object and
        sets backup_codes_remaining as a plain attribute so Pydantic's
        from_attributes mapper can pick it up like any other field.

        Also handles plain-dict inputs (e.g. test fixtures) that already carry the
        computed key.
        """
        if hasattr(data, "backup_codes"):
            # ORM object: derive count and attach as a normal attribute
            codes = getattr(data, "backup_codes", None)
            count = len(codes) if codes else 0
            # SQLAlchemy mapped objects are not frozen; plain setattr is safe
            setattr(data, "backup_codes_remaining", count)
        elif isinstance(data, dict) and "backup_codes_remaining" not in data:
            data["backup_codes_remaining"] = 0
        # Plain-dict inputs that already include backup_codes_remaining pass through
        return data


class LoginResponse(BaseModel):
    """Replaces TokenResponse for /auth/login. One of access_token or a challenge token is set."""

    access_token: str | None = None
    token_type: str = "bearer"
    mfa_challenge_token: str | None = None  # user has MFA; must verify
    mfa_setup_token: str | None = None      # org requires MFA; user must enroll
    user: UserOut | None = None             # absent until MFA confirmed

    @model_validator(mode="after")
    def check_exactly_one_token(self) -> "LoginResponse":
        tokens = [self.access_token, self.mfa_challenge_token, self.mfa_setup_token]
        non_none = sum(1 for t in tokens if t is not None)
        if non_none != 1:
            raise ValueError(
                "Exactly one of access_token, mfa_challenge_token, mfa_setup_token must be set"
            )
        return self


class MFAVerifyRequest(BaseModel):
    code: str  # 6-digit TOTP or "xxxx-xxxx" backup code

    @field_validator("code")
    @classmethod
    def validate_code_format(cls, v: str) -> str:
        v = v.strip()
        if len(v) == 6 and v.isdigit():
            return v  # TOTP code
        if len(v) == 9 and v[4] == "-" and len(v[:4]) == 4 and len(v[5:]) == 4:
            return v  # backup code: xxxx-xxxx
        raise ValueError("Code must be a 6-digit TOTP code or a backup code in xxxx-xxxx format")


class MFASetupInitResponse(BaseModel):
    secret_uri: str  # otpauth:// URI — client renders as QR


class MFASetupCompleteResponse(BaseModel):
    """Returned by POST /auth/mfa/setup/complete on success."""

    access_token: str
    token_type: str = "bearer"
    backup_codes: list[str]  # 10 plain codes, shown once — stored hashed, never retrievable again
    user: UserOut


class BackupCodesResponse(BaseModel):
    codes: list[str]  # 10 plain codes, shown once after regeneration
