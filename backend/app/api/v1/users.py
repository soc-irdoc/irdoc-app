"""
User management + invite endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permission
from app.core.security import hash_password
from app.models.user import User
from app.schemas.admin import (
    InviteAccept,
    InviteCreate,
    InviteOut,
    UserOut,
    UserRoleUpdate,
)
from app.services import auth_service, invite_service, email_service, audit_service

router = APIRouter(prefix="/users", tags=["users"])

# Reuse the same cookie settings as auth.py
from app.core.config import settings
REFRESH_COOKIE_NAME = "refresh_token"
COOKIE_SETTINGS = {
    "httponly": True,
    "samesite": "strict",
    "secure": settings.COOKIE_SECURE,
    "max_age": settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
}


@router.get("")
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("users.read")),
):
    """List all users in the org."""
    import uuid
    result = await db.execute(
        select(User)
        .where(User.org_id == uuid.UUID(str(current_user.org_id)), User.is_active == True)  # noqa: E712
        .order_by(User.full_name)
    )
    users = result.scalars().all()
    return {
        "data": [UserOut.model_validate(u) for u in users],
        "meta": {"total": len(users)},
        "error": None,
    }


@router.put("/{user_id}/role")
async def update_user_role(
    user_id: str,
    data: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("users.manage")),
):
    """Change a user's role. Cannot remove the last admin."""
    import uuid

    result = await db.execute(
        select(User).where(
            User.id == uuid.UUID(user_id),
            User.org_id == uuid.UUID(str(current_user.org_id)),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent removing the last admin
    if user.role == "admin" and data.role != "admin":
        count_result = await db.execute(
            select(func.count()).select_from(User).where(
                User.org_id == uuid.UUID(str(current_user.org_id)),
                User.role == "admin",
                User.is_active == True,  # noqa: E712
            )
        )
        admin_count = count_result.scalar() or 0
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last admin in the organization",
            )

    old_role = user.role
    user.role = data.role
    await db.flush()
    await db.commit()

    await audit_service.log(
        db,
        org_id=str(current_user.org_id),
        user_id=str(current_user.id),
        action="user.role_changed",
        entity_type="user",
        entity_id=user_id,
        diff={"old_role": old_role, "new_role": data.role},
    )
    await db.commit()

    return {"data": UserOut.model_validate(user), "error": None}


@router.put("/{user_id}/deactivate")
async def deactivate_user(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("users.manage")),
):
    """Deactivate a user account (soft delete)."""
    import uuid

    result = await db.execute(
        select(User).where(
            User.id == uuid.UUID(user_id),
            User.org_id == uuid.UUID(str(current_user.org_id)),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if str(user.id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    # Prevent deactivating the last admin
    if user.role == "admin":
        count_result = await db.execute(
            select(func.count()).select_from(User).where(
                User.org_id == uuid.UUID(str(current_user.org_id)),
                User.role == "admin",
                User.is_active == True,  # noqa: E712
            )
        )
        admin_count = count_result.scalar() or 0
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the last admin in the organization",
            )

    user.is_active = False
    await db.flush()
    await db.commit()

    await audit_service.log(
        db,
        org_id=str(current_user.org_id),
        user_id=str(current_user.id),
        action="user.deactivated",
        entity_type="user",
        entity_id=user_id,
        actor_label=current_user.email,
        entity_label=user.email,
        risk_level="high",
        request=request,
    )
    await db.commit()

    return {"data": {"ok": True}, "error": None}


@router.put("/{user_id}/reactivate")
async def reactivate_user(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("users.manage")),
):
    """Reactivate a previously deactivated user account."""
    import uuid

    result = await db.execute(
        select(User).where(
            User.id == uuid.UUID(user_id),
            User.org_id == current_user.org_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_active:
        raise HTTPException(status_code=400, detail="User is already active")

    user.is_active = True
    await db.flush()
    await db.commit()

    await audit_service.log(
        db,
        org_id=str(current_user.org_id),
        action="user.reactivated",
        entity_type="user",
        entity_id=user_id,
        actor_label=current_user.email,
        entity_label=user.email,
        user_id=str(current_user.id),
        request=request,
    )
    await db.commit()

    return {"data": {"ok": True}, "error": None}


@router.post("/invite", status_code=201)
async def create_invite(
    data: InviteCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("users.manage")),
):
    """Send an invite email to a new user."""
    invite = await invite_service.create_invite(
        db,
        org_id=str(current_user.org_id),
        invited_by_id=str(current_user.id),
        email=str(data.email),
        role=data.role,
    )
    await db.commit()
    await db.refresh(invite)

    await audit_service.log(
        db,
        org_id=str(current_user.org_id),
        user_id=str(current_user.id),
        action="user.invited",
        entity_type="user_invite",
        entity_id=str(invite.id),
        diff={"email": str(data.email), "role": data.role},
    )
    await db.commit()

    # Load org name for the email
    from app.models.organization import Organization
    import uuid
    org_result = await db.execute(
        select(Organization).where(
            Organization.id == uuid.UUID(str(current_user.org_id))
        )
    )
    org = org_result.scalar_one_or_none()
    org_name = org.name if org else "IRDoc"

    # Fire-and-forget — don't fail the request if email fails
    try:
        await email_service.send_invite_email(
            to=str(data.email),
            inviter_name=current_user.full_name,
            org_name=org_name,
            token=invite.token,
            db=db,
            org_id=str(current_user.org_id),
        )
    except Exception:
        import logging
        logging.getLogger(__name__).warning(
            "Failed to send invite email to %s", data.email, exc_info=True
        )

    out = InviteOut(
        id=str(invite.id),
        email=invite.email,
        role=invite.role,
        expires_at=invite.expires_at,
        accepted_at=invite.accepted_at,
        invited_by_name=current_user.full_name,
    )
    return {"data": out, "error": None}


@router.get("/invite/{token}")
async def validate_invite(token: str, db: AsyncSession = Depends(get_db)):
    """Validate an invite token (public — no auth required)."""
    from datetime import datetime, timezone

    invite = await invite_service.get_invite_by_token(db, token)
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found"
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

    # Load org name
    from app.models.organization import Organization
    import uuid
    org_result = await db.execute(
        select(Organization).where(
            Organization.id == uuid.UUID(str(invite.org_id))
        )
    )
    org = org_result.scalar_one_or_none()

    return {
        "data": {
            "email": invite.email,
            "role": invite.role,
            "org_name": org.name if org else "IRDoc",
            "expires_at": invite.expires_at.isoformat(),
        },
        "error": None,
    }


@router.post("/invite/{token}/accept", status_code=201)
async def accept_invite(
    token: str,
    data: InviteAccept,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Accept an invite and create a new user account. Returns access token + sets refresh cookie."""
    password_hash = hash_password(data.password)
    invite = await invite_service.accept_invite(
        db, token, data.full_name, password_hash
    )
    await db.commit()

    # Fetch the newly created user
    result = await db.execute(select(User).where(User.email == invite.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User creation failed",
        )

    access, refresh = auth_service.issue_tokens(user)
    response.set_cookie(REFRESH_COOKIE_NAME, refresh, **COOKIE_SETTINGS)

    await audit_service.log(
        db,
        org_id=str(user.org_id),
        user_id=str(user.id),
        action="user.created",
        entity_type="user",
        entity_id=str(user.id),
        diff={"email": user.email, "role": user.role, "via": "invite"},
    )
    await db.commit()

    from app.schemas.auth import TokenResponse, UserOut as AuthUserOut
    return {
        "data": TokenResponse(access_token=access),
        "user": AuthUserOut.model_validate(user),
        "error": None,
    }


@router.get("/invites")
async def list_invites(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("users.manage")),
):
    """List pending invites for the org."""
    invites = await invite_service.list_invites(db, str(current_user.org_id))

    # Batch fetch all inviters in a single query to avoid N+1
    inviter_ids = {inv.invited_by for inv in invites if inv.invited_by}
    if inviter_ids:
        inviters_result = await db.execute(
            select(User).where(User.id.in_(list(inviter_ids)))
        )
        inviter_map = {str(u.id): u.full_name for u in inviters_result.scalars()}
    else:
        inviter_map = {}

    out = []
    for inv in invites:
        inviter_name = inviter_map.get(str(inv.invited_by)) if inv.invited_by else None
        out.append(InviteOut(
            id=str(inv.id),
            email=inv.email,
            role=inv.role,
            expires_at=inv.expires_at,
            accepted_at=inv.accepted_at,
            invited_by_name=inviter_name,
        ))

    return {
        "data": out,
        "meta": {"total": len(out)},
        "error": None,
    }


@router.post("/{user_id}/mfa/reset")
async def reset_user_mfa(
    user_id: str,
    current_user: User = Depends(require_permission("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: clear MFA for a user so they re-enroll on next login."""
    from uuid import UUID
    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")

    target = await db.get(User, uid)
    if not target or target.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="User not found")

    target.mfa_enabled = False
    target.totp_secret = None
    target.backup_codes = None
    target.mfa_enrolled_at = None
    await db.commit()
    return {"data": {"detail": "MFA reset"}, "meta": {}, "error": None}


@router.delete("/invites/{invite_id}", status_code=204)
async def revoke_invite(
    invite_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("users.manage")),
):
    """Revoke (delete) a pending invite."""
    await invite_service.revoke_invite(db, invite_id, str(current_user.org_id))
    await db.commit()
