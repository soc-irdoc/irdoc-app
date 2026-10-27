"""
Login sessions: idle timeout, absolute lifetime and revocation (#123).

A session is the refresh cookie. Every refresh issues a new one, so before
0.1.8 a session that kept refreshing never ended. Now:

- Idle timeout: the refresh token expires `idle_minutes` after it was issued.
  The frontend only refreshes while the user is active, so an idle session
  runs out on the server too, not just in the open tab.
- Absolute lifetime: the token carries `auth_time` (the original sign-in),
  which every refresh keeps. After `max_hours` the user must sign in again,
  however active they were.
- Revocation: the token carries the user's `token_version` (`tv`). Bumping it
  (password change, "sign out everywhere") ends every other session at its
  next refresh.

Both limits default to SESSION_IDLE_TIMEOUT_MINUTES / SESSION_MAX_HOURS and
can be overridden per org in Org Settings (organizations.settings JSONB).
"""
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.models.organization import Organization
from app.models.user import User

REFRESH_COOKIE_NAME = "refresh_token"

IDLE_MINUTES_MIN, IDLE_MINUTES_MAX = 5, 1440
MAX_HOURS_MIN, MAX_HOURS_MAX = 1, 720


@dataclass(frozen=True)
class SessionPolicy:
    idle_minutes: int
    max_hours: int


def policy_from_org_settings(org_settings: dict | None) -> SessionPolicy:
    """The org's overrides where set, else the env defaults."""
    org_settings = org_settings or {}
    return SessionPolicy(
        idle_minutes=int(org_settings.get("session_idle_minutes") or settings.SESSION_IDLE_TIMEOUT_MINUTES),
        max_hours=int(org_settings.get("session_max_hours") or settings.SESSION_MAX_HOURS),
    )


async def get_policy(db: AsyncSession, org_id) -> SessionPolicy:
    org = await db.get(Organization, org_id) if org_id else None
    return policy_from_org_settings(org.settings if org else None)


def session_meta(policy: SessionPolicy, auth_time: datetime) -> dict:
    """What the frontend needs to time the session out like the server does."""
    return {
        "idle_minutes": policy.idle_minutes,
        "expires_at": (auth_time + timedelta(hours=policy.max_hours)).isoformat(),
    }


def start_session(
    response: Response,
    user: User,
    policy: SessionPolicy,
    *,
    mfa_verified: bool = False,
    auth_time: datetime | None = None,
) -> tuple[str, dict]:
    """Set the refresh cookie and return (access_token, session_meta).

    auth_time is the original sign-in; pass it when continuing a session
    (refresh) so the absolute lifetime keeps counting from there.
    """
    now = datetime.now(UTC)
    auth_time = auth_time or now
    hard_end = auth_time + timedelta(hours=policy.max_hours)
    refresh_exp = min(now + timedelta(minutes=policy.idle_minutes), hard_end)
    access_exp = min(now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), hard_end)

    org_id = str(user.org_id) if user.org_id else ""
    access = create_access_token(str(user.id), org_id, expires_at=access_exp)
    refresh = create_refresh_token(
        str(user.id),
        org_id,
        expires_at=refresh_exp,
        auth_time=auth_time,
        token_version=user.token_version or 0,
        mfa_verified=mfa_verified,
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh,
        httponly=True,
        samesite="strict",
        secure=settings.COOKIE_SECURE,
        max_age=max(int((refresh_exp - now).total_seconds()), 0),
    )
    return access, session_meta(policy, auth_time)


async def open_session(
    db: AsyncSession,
    response: Response,
    user: User,
    *,
    mfa_verified: bool = False,
) -> tuple[str, dict]:
    """Start a new session after a sign-in (password, MFA, SSO, invite...)."""
    policy = await get_policy(db, user.org_id)
    return start_session(response, user, policy, mfa_verified=mfa_verified)


def continue_session(
    response: Response,
    user: User,
    policy: SessionPolicy,
    refresh_payload: dict,
) -> tuple[str, dict]:
    """Refresh: check the session may go on, then issue the next tokens."""
    raw_auth_time = refresh_payload.get("auth_time")
    if raw_auth_time is None:
        # Issued before 0.1.8, which had no absolute lifetime.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    if refresh_payload.get("tv", 0) != (user.token_version or 0):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Session revoked")
    auth_time = datetime.fromtimestamp(raw_auth_time, UTC)
    if datetime.now(UTC) >= auth_time + timedelta(hours=policy.max_hours):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    return start_session(
        response,
        user,
        policy,
        mfa_verified=bool(refresh_payload.get("mfa_verified", False)),
        auth_time=auth_time,
    )


def revoke_all_sessions(user: User) -> None:
    """End every session of this user at its next refresh. Caller flushes."""
    user.token_version = (user.token_version or 0) + 1


def end_session(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE_NAME)
