"""
SAML 2.0 SSO endpoints.
- GET  /auth/saml/metadata  — SP metadata XML (public)
- POST /auth/saml/acs       — Assertion Consumer Service (public)
- GET  /auth/saml/login     — Initiate SSO login (public)

Enterprise feature — check_feature("sso_saml") before any SAML operation.
All python3-saml errors are caught and never leaked to the client.
"""
import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.feature_flags import check_feature
from app.models.organization import Organization
from app.models.user import User
from app.services import auth_service, sso_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/saml", tags=["saml"])

REFRESH_COOKIE_NAME = "refresh_token"
COOKIE_SETTINGS = {
    "httponly": True,
    "samesite": "strict",
    "secure": False,
    "max_age": settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
}


def _check_sso_feature():
    if not check_feature("sso_saml"):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="SSO/SAML requires an enterprise license",
        )


async def _get_default_sso_config(db: AsyncSession):
    """For single-org deployments, use the default org's SSO config."""
    result = await db.execute(
        select(Organization).where(Organization.slug == "default")
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No default organization configured",
        )
    cfg = await sso_service.get_sso_config(db, str(org.id))
    if not cfg or not cfg.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SSO is not configured or not enabled for this organization",
        )
    return org, cfg


@router.get("/metadata")
async def saml_metadata(db: AsyncSession = Depends(get_db)):
    """Return SP metadata XML. Public endpoint."""
    _check_sso_feature()

    try:
        from onelogin.saml2.settings import OneLogin_Saml2_Settings

        org, cfg = await _get_default_sso_config(db)
        saml_settings_dict = await sso_service.get_saml_settings(
            cfg, str(settings.BASE_URL)
        )
        saml_settings = OneLogin_Saml2_Settings(
            settings=saml_settings_dict, sp_validation_only=True
        )
        metadata = saml_settings.get_sp_metadata()
        errors = saml_settings.validate_metadata(metadata)
        if errors:
            logger.warning("SAML metadata validation errors: %s", errors)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("SAML metadata generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate SAML metadata",
        )

    return Response(content=metadata, media_type="application/xml")


@router.get("/login")
async def saml_login(db: AsyncSession = Depends(get_db)):
    """Initiate a SAML SSO login. Returns a redirect URL to the IdP."""
    _check_sso_feature()

    try:
        from onelogin.saml2.auth import OneLogin_Saml2_Auth

        org, cfg = await _get_default_sso_config(db)
        saml_settings_dict = await sso_service.get_saml_settings(
            cfg, str(settings.BASE_URL)
        )

        # Build a minimal request dict for python3-saml
        req = {
            "https": "off",
            "http_host": str(settings.BASE_URL).replace("https://", "").replace("http://", ""),
            "script_name": "/auth/saml/acs",
            "server_port": "",
            "get_data": {},
            "post_data": {},
        }
        auth = OneLogin_Saml2_Auth(req, old_settings=saml_settings_dict)
        redirect_url = auth.login()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("SAML login initiation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate SSO login",
        )

    return {"data": {"redirect_url": redirect_url}, "error": None}


@router.post("/acs")
async def saml_acs(
    request: Request,
    SAMLResponse: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """
    SAML Assertion Consumer Service.
    Validates the SAML response, creates or updates the user, issues JWT.
    Redirects to BASE_URL on success.
    """
    _check_sso_feature()

    try:
        from onelogin.saml2.auth import OneLogin_Saml2_Auth

        org, cfg = await _get_default_sso_config(db)
        saml_settings_dict = await sso_service.get_saml_settings(
            cfg, str(settings.BASE_URL)
        )

        # Build request dict for python3-saml
        form_data = await request.form()
        req = {
            "https": "on" if request.url.scheme == "https" else "off",
            "http_host": request.headers.get("host", "localhost"),
            "script_name": request.url.path,
            "server_port": str(request.url.port or ""),
            "get_data": dict(request.query_params),
            "post_data": dict(form_data),
        }

        auth = OneLogin_Saml2_Auth(req, old_settings=saml_settings_dict)
        auth.process_response()
        errors = auth.get_errors()

        if errors:
            logger.warning("SAML ACS errors: %s — %s", errors, auth.get_last_error_reason())
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="SAML authentication failed",
            )

        if not auth.is_authenticated():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="SAML authentication failed — not authenticated",
            )

        # Extract attributes
        attrs = auth.get_attributes()
        name_id = auth.get_nameid()

        email_attr = cfg.attr_email or "email"
        name_attr = cfg.attr_name or "displayName"
        groups_attr = cfg.attr_groups or "groups"

        # Get email from attributes or NameID
        email_values = attrs.get(email_attr, [])
        email = email_values[0] if email_values else name_id
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SAML response missing email attribute",
            )
        email = email.lower()

        name_values = attrs.get(name_attr, [])
        full_name = name_values[0] if name_values else email.split("@")[0]

        # Determine role from group mappings
        groups = attrs.get(groups_attr, [])
        role = "analyst"  # default
        role_mappings: dict = cfg.role_mappings or {}
        for group in groups:
            if group in role_mappings:
                role = role_mappings[group]
                break

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("SAML ACS processing failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SAML authentication processing failed",
        )

    # Create or update the user
    try:
        existing = await auth_service.get_user_by_email(db, email)
        if existing:
            # Update name if changed
            if full_name and existing.full_name != full_name:
                existing.full_name = full_name
                initials = "".join(part[0].upper() for part in full_name.split()[:2])
                existing.avatar_initials = initials or full_name[:2].upper()
            user = existing
        else:
            # Auto-provision new user
            from app.core.security import hash_password
            import secrets
            # Random password — user will only log in via SSO
            temp_password = secrets.token_urlsafe(32)
            user = await auth_service.register_user(
                db,
                email=email,
                full_name=full_name,
                password=temp_password,
                org_id=str(org.id),
                role=role,
            )

        await db.commit()
    except Exception as exc:
        logger.error("User create/update during SAML ACS failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to provision user account",
        )

    access, refresh_token = auth_service.issue_tokens(user)

    # Redirect to frontend with access token in query param (short-lived, one-time)
    # The frontend should exchange this immediately and store in Zustand memory only.
    redirect_url = f"{str(settings.BASE_URL).rstrip('/')}/?sso_token={access}"
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(REFRESH_COOKIE_NAME, refresh_token, **COOKIE_SETTINGS)
    return response
