"""SSO/OIDC config management - reading and writing org SSO settings."""
import base64
import re
import uuid as _uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sso_config import SSOConfig


def _fernet():
    """
    Derive a Fernet key from SECRET_KEY using HKDF-SHA256 with a domain-specific
    info label. HKDF ensures the derived key is uniformly distributed regardless
    of the input key's format, and the label isolates it from other derived keys.
    """
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF

    from app.core.config import settings

    key_material = settings.SECRET_KEY.encode()
    derived = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"irdoc-sso-client-secret-v1",
    ).derive(key_material)
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt_client_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_client_secret(encrypted: str) -> str:
    return _fernet().decrypt(encrypted.encode()).decode()


async def get_sso_config(db: AsyncSession, org_id: str) -> SSOConfig | None:
    result = await db.execute(
        select(SSOConfig).where(SSOConfig.org_id == _uuid.UUID(str(org_id)))
    )
    return result.scalar_one_or_none()


async def upsert_sso_config(db: AsyncSession, org_id: str, data: dict) -> SSOConfig:
    from datetime import datetime, timezone

    # Encrypt client_secret before persisting - only when a new value is supplied
    if data.get("client_secret"):
        data = dict(data)
        data["client_secret"] = encrypt_client_secret(data["client_secret"])

    existing = await get_sso_config(db, org_id)
    if existing:
        for key, value in data.items():
            if value is not None and hasattr(existing, key):
                setattr(existing, key, value)
        existing.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return existing

    config = SSOConfig(
        org_id=_uuid.UUID(str(org_id)),
        **{k: v for k, v in data.items() if hasattr(SSOConfig, k) and v is not None},
    )
    db.add(config)
    await db.flush()
    return config


def redirect_uri() -> str:
    """The OIDC callback URL, which must match the App Registration's."""
    from app.core.config import settings

    return f"{str(settings.BASE_URL).rstrip('/')}/api/v1/auth/oidc/callback"


# ─── Role mapping (Refs #172) ────────────────────────────────────────────────

_GUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
# Zero-width characters ride along when a GUID is copied out of the Entra portal
_INVISIBLE = dict.fromkeys(map(ord, "​‌‍⁠﻿"))


def _norm(value) -> str:
    """Comparable form of a mapping key or token value: no surrounding space,
    braces or invisible characters, lower case."""
    return str(value).translate(_INVISIBLE).strip().strip("{}").strip().lower()


def looks_like_guid(value) -> bool:
    return bool(_GUID_RE.match(_norm(value)))


def _mapping_candidates(claims: dict) -> set[str]:
    """Every token value a role mapping may be keyed on: group object IDs
    (`groups`), app roles (`roles`) and the user's own object ID (`oid`)."""
    values: list = []
    for claim in ("groups", "roles"):
        raw = claims.get(claim) or []
        values.extend(raw if isinstance(raw, list) else [raw])
    if claims.get("oid"):
        values.append(claims["oid"])
    return {_norm(v) for v in values if v}


def match_sso_role(claims: dict, role_mappings: dict | None) -> tuple[str | None, str | None]:
    """(role, mapping key) an SSO sign-in maps to, or (None, None).

    When several mappings match, the most privileged role wins. Keys are
    compared after `_norm`, and mappings to unknown roles are ignored.
    """
    from app.core.permissions import ROLE_HIERARCHY

    if not role_mappings:
        return None, None
    candidates = _mapping_candidates(claims)
    matched = [
        (role, key)
        for key, role in role_mappings.items()
        if _norm(key) in candidates and role in ROLE_HIERARCHY
    ]
    if not matched:
        return None, None
    return max(matched, key=lambda m: ROLE_HIERARCHY[m[0]])


def resolve_sso_role(claims: dict, role_mappings: dict | None) -> str | None:
    """Role an SSO sign-in maps to, or None when no mapping matches."""
    return match_sso_role(claims, role_mappings)[0]


# ─── Microsoft Graph group lookup ────────────────────────────────────────────

GRAPH_SCOPE = "https://graph.microsoft.com/User.Read"
_GRAPH_CHECK_GROUPS = "https://graph.microsoft.com/v1.0/me/checkMemberGroups"
_GRAPH_BATCH = 20  # API limit per request


async def fetch_member_groups(access_token: str, group_ids: list[str]) -> set[str]:
    """Which of `group_ids` the signed-in user belongs to, nested membership
    included. Uses Graph's checkMemberGroups, which needs only User.Read for
    /me and answers with Object IDs whatever format the token's groups claim
    uses. Raises on any failure; the caller decides how to degrade."""
    found: set[str] = set()
    async with httpx.AsyncClient() as client:
        for i in range(0, len(group_ids), _GRAPH_BATCH):
            resp = await client.post(
                _GRAPH_CHECK_GROUPS,
                headers={"Authorization": f"Bearer {access_token}"},
                json={"groupIds": group_ids[i:i + _GRAPH_BATCH]},
                timeout=10.0,
            )
            resp.raise_for_status()
            found.update(_norm(g) for g in resp.json().get("value", []))
    return found


# ─── Connection test ─────────────────────────────────────────────────────────

_LOGIN = "https://login.microsoftonline.com"

# AADSTS codes an admin can act on, in plain words
_AADSTS_MESSAGES = {
    "90002": "Tenant not found. Check the Directory (Tenant) ID.",
    "900023": "The Directory (Tenant) ID is not a valid tenant.",
    "700016": "Application not found in this tenant. Check the Application (Client) ID, "
              "and that the app is registered in this tenant.",
    "7000215": "Invalid client secret. Use the secret's Value, not its Secret ID.",
    "7000222": "The client secret has expired. Create a new one in the App Registration.",
    "7000216": "The client secret is missing.",
}
_AADSTS_RE = re.compile(r"AADSTS(\d+)")


def _describe_token_error(body: dict) -> str:
    desc = str(body.get("error_description") or body.get("error") or "Unknown error")
    code = _AADSTS_RE.search(desc)
    if code and code.group(1) in _AADSTS_MESSAGES:
        return f"{_AADSTS_MESSAGES[code.group(1)]} (AADSTS{code.group(1)})"
    # Drop the Trace ID / Correlation ID / Timestamp lines Entra appends
    return desc.split("\r\n")[0].split(" Trace ID:")[0].strip()


async def check_connection(tenant_id: str, client_id: str, client_secret: str) -> dict:
    """Check that the tenant exists and that the client ID and secret are valid.

    Returns {"ok", "step", "message"}. The token request uses the client
    credentials grant against Graph's .default scope, which succeeds for any
    valid app registration whatever API permissions it has. The redirect URI
    can't be checked this way; the caller shows it for comparison.
    """
    tenant_id, client_id = tenant_id.strip(), client_id.strip()
    try:
        async with httpx.AsyncClient() as client:
            disco = await client.get(
                f"{_LOGIN}/{tenant_id}/v2.0/.well-known/openid-configuration", timeout=10.0,
            )
            if disco.status_code != 200:
                return {"ok": False, "step": "tenant",
                        "message": _describe_token_error(_safe_json(disco))}
            keys = await client.get(f"{_LOGIN}/{tenant_id}/discovery/v2.0/keys", timeout=10.0)
            if keys.status_code != 200 or not _safe_json(keys).get("keys"):
                return {"ok": False, "step": "tenant",
                        "message": "Could not fetch the tenant's signing keys."}

            token = await client.post(
                f"{_LOGIN}/{tenant_id}/oauth2/v2.0/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                },
                timeout=10.0,
            )
            if token.status_code != 200:
                return {"ok": False, "step": "credentials",
                        "message": _describe_token_error(_safe_json(token))}
    except httpx.HTTPError as exc:
        return {"ok": False, "step": "network",
                "message": f"Could not reach login.microsoftonline.com ({type(exc).__name__})."}
    return {"ok": True, "step": "done",
            "message": "Tenant, Client ID and Client Secret are valid."}


def _safe_json(resp) -> dict:
    try:
        body = resp.json()
        return body if isinstance(body, dict) else {}
    except ValueError:
        return {}


async def provision_oidc_user(
    db: AsyncSession,
    *,
    org,
    email: str,
    full_name: str,
    mapped_role: str | None,
):
    """Create or update the user behind an SSO sign-in.

    A matched role mapping is applied on every sign-in, so Entra stays the source
    of truth for mapped users. Without a match, a new user gets "analyst" and an
    existing user keeps whatever role they have (e.g. one set by hand).
    """
    import logging
    import secrets

    from app.services import audit_service, auth_service

    logger = logging.getLogger(__name__)

    user = await auth_service.get_user_by_email(db, email)
    if user is None:
        user = await auth_service.register_user(
            db,
            email=email,
            full_name=full_name,
            password=secrets.token_urlsafe(32),
            org_id=str(org.id),
            role=mapped_role or "analyst",
        )
        user.auth_provider = "oidc"
        return user

    if full_name and user.full_name != full_name:
        user.full_name = full_name
        initials = "".join(p[0].upper() for p in full_name.split()[:2])
        user.avatar_initials = initials or full_name[:2].upper()
    user.auth_provider = "oidc"

    if not mapped_role or user.role == mapped_role:
        return user

    # Only sync roles onto accounts in the org this SSO config belongs to
    if str(user.org_id) != str(org.id):
        logger.warning("SSO role mapping skipped for %s: account belongs to another org", email)
        return user

    # Same invariant as the manual role endpoint: never demote the last admin
    if user.role == "admin" and mapped_role != "admin":
        from sqlalchemy import func

        from app.models.user import User

        admin_count = (await db.execute(
            select(func.count()).select_from(User).where(
                User.org_id == user.org_id,
                User.role == "admin",
                User.is_active == True,  # noqa: E712
            )
        )).scalar() or 0
        if admin_count <= 1:
            logger.warning(
                "SSO role mapping would demote %s, the last admin, to %s - keeping admin",
                email, mapped_role,
            )
            return user

    old_role = user.role
    user.role = mapped_role
    logger.info("SSO role mapping changed %s from %s to %s", email, old_role, mapped_role)
    await audit_service.log(
        db,
        org_id=str(user.org_id),
        user_id=str(user.id),
        actor_label="SSO",
        action="user.role_changed",
        entity_type="user",
        entity_id=str(user.id),
        entity_label=email,
        diff={"old_role": old_role, "new_role": mapped_role, "via": "sso"},
    )
    return user
