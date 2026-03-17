"""User invite CRUD."""
import secrets
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_invite import UserInvite
from app.models.user import User


async def create_invite(
    db: AsyncSession,
    org_id: str,
    invited_by_id: str,
    email: str,
    role: str,
) -> UserInvite:
    """Create a new invite token for the given email. One active invite per email per org."""
    import uuid as _uuid

    token = secrets.token_urlsafe(32)
    invite = UserInvite(
        org_id=_uuid.UUID(str(org_id)),
        invited_by=_uuid.UUID(str(invited_by_id)),
        email=email.lower(),
        role=role,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
    )
    db.add(invite)
    await db.flush()
    return invite


async def get_invite_by_token(db: AsyncSession, token: str) -> UserInvite | None:
    """Return the invite matching a token, or None."""
    result = await db.execute(
        select(UserInvite).where(UserInvite.token == token)
    )
    return result.scalar_one_or_none()


async def accept_invite(
    db: AsyncSession,
    token: str,
    full_name: str,
    password_hash: str,
) -> UserInvite:
    """
    Validate an invite token (not expired, not already accepted), create the user,
    and mark the invite as accepted. Returns the updated invite.
    """
    import uuid as _uuid

    invite = await get_invite_by_token(db, token)
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )
    if invite.accepted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invitation has already been accepted",
        )
    if datetime.now(timezone.utc) > invite.expires_at:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invitation has expired",
        )

    # Check if user with this email already exists
    existing = await db.execute(
        select(User).where(User.email == invite.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    initials = "".join(part[0].upper() for part in full_name.split()[:2])
    user = User(
        org_id=invite.org_id,
        email=invite.email,
        full_name=full_name,
        role=invite.role,
        password_hash=password_hash,
        avatar_initials=initials or full_name[:2].upper(),
    )
    db.add(user)

    invite.accepted_at = datetime.now(timezone.utc)
    await db.flush()

    return invite


async def list_invites(db: AsyncSession, org_id: str) -> list[UserInvite]:
    """Return pending (not accepted, not expired) invites for an org."""
    import uuid as _uuid

    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(UserInvite).where(
            UserInvite.org_id == _uuid.UUID(str(org_id)),
            UserInvite.accepted_at.is_(None),
            UserInvite.expires_at > now,
        ).order_by(UserInvite.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_invite(
    db: AsyncSession,
    invite_id: str,
    org_id: str,
) -> None:
    """Delete an invite if it belongs to the org. Raises 404 if not found."""
    import uuid as _uuid

    result = await db.execute(
        select(UserInvite).where(
            UserInvite.id == _uuid.UUID(str(invite_id)),
            UserInvite.org_id == _uuid.UUID(str(org_id)),
        )
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )
    await db.delete(invite)
    await db.flush()
