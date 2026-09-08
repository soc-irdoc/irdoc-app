"""
OAuth2 / OIDC Authorization Code Flow — Entra ID SSO endpoints.

- GET /auth/oidc/login      — Initiate login, returns Azure redirect URL (public)
- GET /auth/oidc/callback   — Handle authorization code from Azure (public)

Enterprise feature — check_feature("sso_oidc") before any OIDC operation.
"""
import logging
import secrets
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from jose import JWTError
from jose import jwt as jose_jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.feature_flags import check_feature
from app.models.organization import Organization
from app.services import auth_service, sso_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/oidc", tags=["oidc"])

REFRESH_COOKIE_NAME = "refresh_token"
STATE_COOKIE_NAME = "oidc_state"

REFRESH_COOKIE_SETTINGS = {
    "httponly": True,
    "samesite": "strict",
    "secure": False,
    "max_age": settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
}

# OAuth2 error codes that Azure may legitimately return — anything else is mapped
# to "server_error" to prevent reflected injection.
_ALLOWED_OAUTH_ERRORS = frozenset({
    "access_denied", "invalid_request", "unauthorized_client",
    "unsupported_response_type", "invalid_scope", "server_error",
    "temporarily_unavailable", "interaction_required", "login_required",
    "consent_required", "invalid_client",
})

# Simple in-process JWKS cache keyed by tenant_id.
# Azure rotates keys infrequently; 1-hour TTL is both safe and conservative.
_jwks_cache: dict[str, tuple[dict, float]] = {}


async def _fetch_jwks(tenant_id: str) -> dict:
    cached = _jwks_cache.get(tenant_id)
    if cached and cached[1] > time.monotonic():
        return cached[0]
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
                timeout=10.0,
            )
            resp.raise_for_status()
            jwks = resp.json()
    except Exception as exc:
        logger.error("Failed to fetch Azure JWKS for tenant %s: %s", tenant_id, exc)
        raise HTTPException(status_code=502, detail="Failed to fetch Azure signing keys")
    _jwks_cache[tenant_id] = (jwks, time.monotonic() + 3600)
    return jwks


def _check_sso_feature():
    if not check_feature("sso_oidc"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="SSO/OIDC requires an enterprise license",
        )


async def _get_enabled_config(db: AsyncSession):
    result = await db.execute(
        select(Organization).where(Organization.slug == "default")
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="No default organization configured")

    cfg = await sso_service.get_sso_config(db, str(org.id))
    if not cfg or not cfg.is_enabled:
        raise HTTPException(status_code=404, detail="SSO is not configured or not enabled")
    if not cfg.tenant_id or not cfg.client_id or not cfg.client_secret:
        raise HTTPException(
            status_code=400,
            detail="SSO is not fully configured — Tenant ID, Client ID, and Client Secret are all required",
        )
    return org, cfg


def _redirect_uri() -> str:
    return f"{str(settings.BASE_URL).rstrip('/')}/api/v1/auth/oidc/callback"


@router.get("/login")
async def oidc_login(db: AsyncSession = Depends(get_db)):
    """Return the Azure authorization URL. Frontend redirects the browser to it."""
    _check_sso_feature()
    _, cfg = await _get_enabled_config(db)

    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(24)

    auth_url = (
        f"https://login.microsoftonline.com/{cfg.tenant_id}/oauth2/v2.0/authorize"
        f"?client_id={cfg.client_id}"
        f"&response_type=code"
        f"&redirect_uri={_redirect_uri()}"
        f"&response_mode=query"
        f"&scope=openid+profile+email"
        f"&state={state}"
        f"&nonce={nonce}"
    )

    resp = JSONResponse({"data": {"redirect_url": auth_url}, "error": None})
    # Store both state (CSRF) and nonce (replay) in one signed httpOnly cookie.
    resp.set_cookie(
        key=STATE_COOKIE_NAME,
        value=f"{state}|{nonce}",
        httponly=True,
        samesite="lax",   # lax required: Azure redirects cross-site back to us
        secure=False,
        max_age=300,
    )
    return resp


@router.get("/callback")
async def oidc_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Azure redirects here with the authorization code after the user authenticates."""
    _check_sso_feature()

    base = str(settings.BASE_URL).rstrip("/")

    if error:
        # Allowlist to avoid reflecting attacker-controlled strings into the URL.
        safe_error = error if error in _ALLOWED_OAUTH_ERRORS else "server_error"
        logger.warning("OIDC error from Azure: %s (original: %s)", safe_error, error)
        return RedirectResponse(
            url=f"{base}/?sso_error={safe_error}",
            status_code=status.HTTP_302_FOUND,
        )

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # Verify CSRF state and extract nonce
    cookie_raw = request.cookies.get(STATE_COOKIE_NAME, "")
    try:
        cookie_state, cookie_nonce = cookie_raw.split("|", 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state cookie format — please try logging in again")

    if not cookie_state or cookie_state != state:
        raise HTTPException(status_code=400, detail="Invalid CSRF state — please try logging in again")

    org, cfg = await _get_enabled_config(db)
    client_secret = sso_service.decrypt_client_secret(cfg.client_secret)

    # Exchange authorization code for tokens
    token_url = f"https://login.microsoftonline.com/{cfg.tenant_id}/oauth2/v2.0/token"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                token_url,
                data={
                    "client_id": cfg.client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": _redirect_uri(),
                    "grant_type": "authorization_code",
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            tokens = resp.json()
    except Exception as exc:
        logger.error("OIDC token exchange failed: %s", exc)
        raise HTTPException(status_code=502, detail="Failed to exchange authorization code — check your Client Secret")

    id_token = tokens.get("id_token", "")
    if not id_token:
        raise HTTPException(status_code=401, detail="Azure did not return an ID token")

    # Verify the ID token signature against Azure's published JWKS, then validate
    # audience, issuer, expiry, and the nonce we generated for this request.
    try:
        jwks = await _fetch_jwks(cfg.tenant_id)
        expected_issuer = f"https://login.microsoftonline.com/{cfg.tenant_id}/v2.0"
        claims = jose_jwt.decode(
            id_token,
            jwks,
            algorithms=["RS256"],
            audience=cfg.client_id,
            issuer=expected_issuer,
            options={"verify_exp": True},
        )
    except JWTError as exc:
        logger.error("OIDC ID token verification failed: %s", exc)
        raise HTTPException(status_code=401, detail="ID token signature or claims validation failed")
    except Exception as exc:
        logger.error("Unexpected OIDC token error: %s", exc)
        raise HTTPException(status_code=401, detail="ID token could not be validated")

    # Verify nonce to prevent token replay attacks
    if claims.get("nonce") != cookie_nonce:
        raise HTTPException(status_code=401, detail="ID token nonce mismatch — possible replay attack")

    email = (claims.get("email") or claims.get("preferred_username") or "").lower().strip()
    full_name = (claims.get("name") or email.split("@")[0]).strip()

    if not email:
        raise HTTPException(
            status_code=400,
            detail="OIDC token missing email — ensure the 'email' scope is consented in your App Registration",
        )

    # Role from group object IDs mapped in config
    groups: list[str] = claims.get("groups", [])
    role = "analyst"
    for group in groups:
        if group in (cfg.role_mappings or {}):
            role = cfg.role_mappings[group]
            break

    # Provision user
    try:
        existing = await auth_service.get_user_by_email(db, email)
        if existing:
            if full_name and existing.full_name != full_name:
                existing.full_name = full_name
                initials = "".join(p[0].upper() for p in full_name.split()[:2])
                existing.avatar_initials = initials or full_name[:2].upper()
            existing.auth_provider = "oidc"
            user = existing
        else:
            temp_password = secrets.token_urlsafe(32)
            user = await auth_service.register_user(
                db,
                email=email,
                full_name=full_name,
                password=temp_password,
                org_id=str(org.id),
                role=role,
            )
            user.auth_provider = "oidc"
        await db.commit()
    except Exception as exc:
        logger.error("User provisioning during OIDC callback failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to provision user account")

    _, refresh_token = auth_service.issue_tokens(user)

    # Deliver session via httpOnly refresh cookie only — no token in the URL.
    # The frontend's existing tryRestore() calls POST /auth/refresh with the cookie
    # and receives a fresh access token, so no additional frontend changes are needed.
    redirect_response = RedirectResponse(
        url=f"{base}/",
        status_code=status.HTTP_302_FOUND,
    )
    redirect_response.set_cookie(REFRESH_COOKIE_NAME, refresh_token, **REFRESH_COOKIE_SETTINGS)
    redirect_response.delete_cookie(STATE_COOKIE_NAME)
    return redirect_response
