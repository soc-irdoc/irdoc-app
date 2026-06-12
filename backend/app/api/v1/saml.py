"""
SAML 2.0 endpoints — REMOVED. IRDoc now uses OAuth2/OIDC for SSO.

All routes return 410 Gone so any bookmarked or cached links get an explicit
signal rather than a confusing 404.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/auth/saml", tags=["saml-deprecated"])

_GONE = JSONResponse(
    status_code=410,
    content={"data": None, "error": "SAML SSO has been replaced by OIDC. Use /api/v1/auth/oidc/login"},
)


@router.get("/metadata")
@router.get("/login")
@router.post("/acs")
async def saml_gone():
    return _GONE
