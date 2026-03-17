"""
Auth service: JWT lifecycle, password management, setup flow.
"""
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.models.user import User
from app.models.organization import Organization


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    user = await get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")

    # Rehash if argon2id params have changed
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    user.last_seen = datetime.now(UTC)
    await db.flush()
    return user


def issue_tokens(user: User) -> tuple[str, str]:
    """Returns (access_token, refresh_token)."""
    org_id = str(user.org_id) if user.org_id else ""
    access = create_access_token(str(user.id), org_id)
    refresh = create_refresh_token(str(user.id), org_id)
    return access, refresh


async def register_user(
    db: AsyncSession,
    email: str,
    full_name: str,
    password: str,
    org_id: str,
    role: str = "analyst",
) -> User:
    existing = await get_user_by_email(db, email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    initials = "".join(part[0].upper() for part in full_name.split()[:2])
    user = User(
        org_id=org_id,
        email=email.lower(),
        full_name=full_name,
        role=role,
        password_hash=hash_password(password),
        avatar_initials=initials or full_name[:2].upper(),
    )
    db.add(user)
    await db.flush()
    return user


async def change_password(db: AsyncSession, user: User, current: str, new: str) -> None:
    if not verify_password(current, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    user.password_hash = hash_password(new)
    user.must_reset_password = False
    await db.flush()


async def setup_complete(db: AsyncSession) -> bool:
    """Returns True if any user exists (setup already done)."""
    result = await db.execute(select(func.count()).select_from(User))
    return (result.scalar() or 0) > 0


async def perform_setup(
    db: AsyncSession,
    email: str,
    full_name: str,
    password: str,
    org_name: str,
) -> User:
    """First-run setup: create default org + admin user."""
    if await setup_complete(db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Setup already completed",
        )

    org = Organization(name=org_name, slug="default", plan="core")
    db.add(org)
    await db.flush()

    user = await register_user(db, email, full_name, password, str(org.id), role="admin")
    return user
