"""
MFA setup endpoints.

GET  /auth/mfa/setup           — Generate a fresh TOTP secret (mfa_setup OR access token)
POST /auth/mfa/setup/complete  — Verify code, enable MFA, return real tokens (mfa_setup OR access token)
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.schemas.auth import (
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
):
    """Accept either an mfa_setup token (forced/voluntary enrollment) or a regular access token."""
    from app.models.user import User  # avoid circular import

    token = credentials.credentials

    # Try mfa_setup token first; fall back to access token
    try:
        payload = decode_token(token, expected_type="mfa_setup")
    except HTTPException:
        payload = decode_token(token, expected_type="access")

    user_id = payload["sub"]
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)  # noqa: E712
    )
    user = result.scalar_one_or_none()
    if not user:
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
    if not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending MFA setup. Call GET /auth/mfa/setup first.",
        )
    if not mfa_service.verify_totp(user.totp_secret, body.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid code. Check your authenticator app.",
        )

    plain_codes, hashed_codes = mfa_service.generate_backup_codes()
    user.mfa_enabled = True
    user.backup_codes = hashed_codes
    user.mfa_enrolled_at = datetime.now(timezone.utc)
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
