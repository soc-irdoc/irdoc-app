"""
MFA endpoints.

GET    /auth/mfa/setup                    — Generate a fresh TOTP secret (mfa_setup OR access token)
POST   /auth/mfa/setup/complete           — Verify code, enable MFA, return real tokens (mfa_setup OR access token)
POST   /auth/mfa/verify                   — Complete MFA challenge login (mfa_challenge token)
POST   /auth/mfa/backup-codes/regenerate  — Regenerate backup codes (access token)
DELETE /auth/mfa/disable                  — Disable MFA (access token)
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt as _jose_jwt
from jose.exceptions import JWTError as _JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import decode_token
from app.schemas.auth import (
    BackupCodesResponse,
    LoginResponse,
    MFASetupCompleteResponse,
    MFASetupInitResponse,
    MFAVerifyRequest,
    UserOut,
)
from app.services import auth_service, mfa_service

router = APIRouter(prefix="/auth/mfa", tags=["mfa"])

_bearer = HTTPBearer(auto_error=True)

REFRESH_COOKIE_NAME = "refresh_token"
COOKIE_SETTINGS = {
    "httponly": True,
    "samesite": "strict",
    "secure": False,
    "max_age": 60 * 60 * 24 * 30,
}


async def _get_user_for_setup(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> "User":
    """Accept either an mfa_setup token (forced/voluntary enrollment) or a regular access token."""
    from app.models.user import User  # avoid circular import

    token = credentials.credentials

    try:
        unverified = _jose_jwt.get_unverified_claims(token)
    except _JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    token_type = unverified.get("type")
    if token_type == "mfa_setup":
        payload = decode_token(token, expected_type="mfa_setup")
    elif token_type == "access":
        payload = decode_token(token, expected_type="access")
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type for MFA setup",
        )

    user = await db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


async def _get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> "User":
    """Dependency: validate a regular access token and return the active user."""
    from app.models.user import User  # avoid circular import

    token = credentials.credentials
    payload = decode_token(token, expected_type="access")
    user = await db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


async def _get_user_for_challenge(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> "User":
    """Dependency: validate an mfa_challenge token and return the active user."""
    from app.models.user import User  # avoid circular import

    token = credentials.credentials
    payload = decode_token(token, expected_type="mfa_challenge")
    user = await db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


@router.get("/setup")
async def get_mfa_setup(
    user=Depends(_get_user_for_setup),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new TOTP secret and store it (pending confirmation)."""
    if user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="MFA is already enabled. Disable it before re-enrolling.",
        )
    raw_secret, uri = mfa_service.generate_totp_secret(user.email)
    user.totp_secret = mfa_service.encrypt_secret(raw_secret)
    await db.commit()
    return {
        "data": MFASetupInitResponse(secret_uri=uri).model_dump(),
        "meta": {},
        "error": None,
    }


@router.post("/setup/complete")
async def complete_mfa_setup(
    body: MFAVerifyRequest,
    response: Response,
    user=Depends(_get_user_for_setup),
    db: AsyncSession = Depends(get_db),
):
    """Verify TOTP code, enable MFA, return real tokens and one-time backup codes."""
    if user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="MFA is already enabled.",
        )
    if not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending MFA setup. Call GET /auth/mfa/setup first.",
        )
    is_valid, counter = mfa_service.verify_totp(user.totp_secret, body.code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid code. Check your authenticator app.",
        )

    plain_codes, hashed_codes = mfa_service.generate_backup_codes()
    user.mfa_enabled = True
    user.backup_codes = hashed_codes
    user.mfa_enrolled_at = datetime.now(timezone.utc)
    user.last_otp_counter = counter
    await db.commit()

    access_token, refresh_token = auth_service.issue_tokens(user)
    response.set_cookie(REFRESH_COOKIE_NAME, refresh_token, **COOKIE_SETTINGS)

    user_out = UserOut.model_validate(user)
    result = MFASetupCompleteResponse(
        access_token=access_token,
        backup_codes=plain_codes,
        user=user_out,
    )
    return {"data": result.model_dump(), "meta": {}, "error": None}


@router.post("/verify")
@limiter.limit("5/minute")
async def verify_mfa(
    request: Request,
    body: MFAVerifyRequest,
    response: Response,
    user=Depends(_get_user_for_challenge),
    db: AsyncSession = Depends(get_db),
):
    """Complete an MFA challenge login. Accepts a 6-digit TOTP code or a backup code."""
    # Backup code path: format is xxxx-xxxx (9 chars, dash at index 4)
    if len(body.code) == 9 and body.code[4] == "-":
        if not mfa_service.verify_backup_code(user, body.code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid backup code",
            )
        await db.commit()  # persist the consumed code removal
    else:
        # TOTP path
        is_valid, counter = mfa_service.verify_totp(
            user.totp_secret, body.code, user.last_otp_counter
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or already-used TOTP code",
            )
        user.last_otp_counter = counter
        await db.commit()

    access_token, refresh_token = auth_service.issue_tokens(user)
    response.set_cookie(REFRESH_COOKIE_NAME, refresh_token, **COOKIE_SETTINGS)

    user_out = UserOut.model_validate(user)
    result = LoginResponse(access_token=access_token, user=user_out)
    return {"data": result.model_dump(), "meta": {}, "error": None}


@router.post("/backup-codes/regenerate")
async def regenerate_backup_codes(
    user=Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate the user's 10 backup codes. Old codes are immediately invalidated."""
    if not user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="MFA is not enabled.",
        )
    plain_codes, hashed_codes = mfa_service.generate_backup_codes()
    user.backup_codes = hashed_codes
    await db.commit()
    return {"data": BackupCodesResponse(codes=plain_codes).model_dump(), "meta": {}, "error": None}


@router.delete("/disable")
async def disable_mfa(
    user=Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable MFA for the current user. Blocked if the org mandates MFA."""
    from app.models.organization import Organization

    org = await db.get(Organization, user.org_id)
    if org and (org.settings or {}).get("mfa_required", False):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="MFA cannot be disabled: your organisation requires it.",
        )

    user.mfa_enabled = False
    user.totp_secret = None
    user.backup_codes = None
    user.mfa_enrolled_at = None
    await db.commit()

    return {"data": {"detail": "MFA disabled"}, "meta": {}, "error": None}
