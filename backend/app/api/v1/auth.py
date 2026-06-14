from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_mfa_challenge_token,
    create_mfa_setup_token,
    get_current_user,
    get_current_user_from_cookie,
)
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    SetupRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserOut,
)
from app.services import audit_service, auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "refresh_token"
COOKIE_SETTINGS = {
    "httponly": True,
    "samesite": "strict",
    "secure": False,  # set True in prod behind HTTPS
    "max_age": settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
}


@router.get("/setup-status")
async def setup_status(db: AsyncSession = Depends(get_db)):
    """Check if first-run setup is needed."""
    done = await auth_service.setup_complete(db)
    return {"setup_complete": done}


@router.post("/setup", status_code=201)
async def setup(data: SetupRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """First-run: create default org + admin user."""
    user = await auth_service.perform_setup(db, data.email, data.full_name, data.password, data.org_name)
    access, refresh = auth_service.issue_tokens(user)
    response.set_cookie(REFRESH_COOKIE_NAME, refresh, **COOKIE_SETTINGS)
    return {"data": TokenResponse(access_token=access), "user": UserOut.model_validate(user)}


@router.post("/register", status_code=201)
async def register(data: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    if not settings.ALLOW_REGISTRATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Open registration is disabled. Contact your admin for an invite.",
        )
    from sqlalchemy import select
    from app.models.organization import Organization
    result = await db.execute(select(Organization).where(Organization.slug == "default"))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No default organization. Complete setup first.",
        )
    user = await auth_service.register_user(db, data.email, data.full_name, data.password, str(org.id))
    access, refresh = auth_service.issue_tokens(user)
    response.set_cookie(REFRESH_COOKIE_NAME, refresh, **COOKIE_SETTINGS)
    return {"data": TokenResponse(access_token=access), "user": UserOut.model_validate(user)}


@router.post("/login")
async def login(data: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    from app.models.organization import Organization

    user = await auth_service.authenticate(db, data.email, data.password)

    if not user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no organisation assigned",
        )

    # ── MFA branching ────────────────────────────────────────────────────────
    if user.mfa_enabled:
        # User has enrolled MFA — must verify TOTP before receiving real tokens
        challenge_token = create_mfa_challenge_token(str(user.id), str(user.org_id))
        return {
            "data": LoginResponse(mfa_challenge_token=challenge_token).model_dump(),
            "meta": {},
            "error": None,
        }

    org = await db.get(Organization, user.org_id)
    mfa_required = (org.settings or {}).get("mfa_required", False) if org else False

    if mfa_required and not user.mfa_enabled:
        # Org policy requires MFA but user hasn't enrolled — must set up first
        setup_token = create_mfa_setup_token(str(user.id), str(user.org_id))
        return {
            "data": LoginResponse(mfa_setup_token=setup_token).model_dump(),
            "meta": {},
            "error": None,
        }
    # ── Normal login ─────────────────────────────────────────────────────────

    access, refresh = auth_service.issue_tokens(user)
    response.set_cookie(REFRESH_COOKIE_NAME, refresh, **COOKIE_SETTINGS)
    await audit_service.log(
        db,
        org_id=str(user.org_id),
        action="user.login",
        entity_type="auth",
        entity_id=str(user.id),
        actor_label=user.email,
        entity_label=user.email,
        user_id=str(user.id),
        request=request,
    )
    await db.commit()
    return {
        "data": LoginResponse(
            access_token=access,
            user=UserOut.model_validate(user),
        ).model_dump(),
        "meta": {},
        "error": None,
    }


@router.post("/refresh")
async def refresh_token(
    response: Response,
    user=Depends(get_current_user_from_cookie),
):
    access, new_refresh = auth_service.issue_tokens(user)
    response.set_cookie(REFRESH_COOKIE_NAME, new_refresh, **COOKIE_SETTINGS)
    return {"data": TokenResponse(access_token=access), "user": UserOut.model_validate(user)}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    response.delete_cookie(REFRESH_COOKIE_NAME)
    await audit_service.log(
        db,
        org_id=str(current_user.org_id),
        action="user.logout",
        entity_type="auth",
        entity_id=str(current_user.id),
        actor_label=current_user.email,
        entity_label=current_user.email,
        user_id=str(current_user.id),
        request=request,
    )
    await db.commit()
    return {"data": {"ok": True}}


@router.get("/me", response_model=UserOut)
async def me(current_user=Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserOut)
async def update_me(
    data: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(current_user, key, value)
    await db.flush()
    return current_user


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await auth_service.change_password(db, current_user, data.current_password, data.new_password)
    return {"data": {"ok": True}}
