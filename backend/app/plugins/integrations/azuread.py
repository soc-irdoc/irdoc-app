"""Azure Active Directory / Entra ID integration (premium)."""
import logging

import httpx

from app.plugins.registry import register_plugin

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_LOGIN_BASE = "https://login.microsoftonline.com"


@register_plugin
class AzureADPlugin:
    name = "azuread"
    display_name = "Azure AD / Entra ID"
    category = "iam"
    is_premium = True
    icon = "🔷"
    description = "Fetch sign-in logs, revoke sessions, and reset passwords via Microsoft Graph."

    config_schema = {
        "tenant_id":     {"type": "string",   "label": "Azure Tenant ID",  "required": True},
        "client_id":     {"type": "string",   "label": "App Client ID",    "required": True},
        "client_secret": {"type": "password", "label": "Client Secret",    "required": True},
    }

    async def test_connection(self, config: dict) -> bool:
        try:
            token = await self._get_token(config)
            return bool(token)
        except Exception:
            return False

    async def get_sign_in_logs(self, user_upn: str, config: dict, limit: int = 50) -> list[dict]:
        """Fetch recent sign-in events for a UPN."""
        try:
            token = await self._get_token(config)
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    f"{_GRAPH_BASE}/auditLogs/signIns",
                    params={
                        "$filter": f"userPrincipalName eq '{user_upn}'",
                        "$top": limit,
                        "$orderby": "createdDateTime desc",
                    },
                    headers={"Authorization": f"Bearer {token}"},
                )
                r.raise_for_status()
                return r.json().get("value", [])
        except Exception as exc:
            logger.warning("AzureAD sign-in logs failed for %s: %s", user_upn, exc)
            return []

    async def revoke_sessions(self, user_id: str, config: dict) -> bool:
        """Revoke all active sessions for a user. Requires confirmation modal + Senior Analyst role."""
        try:
            token = await self._get_token(config)
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    f"{_GRAPH_BASE}/users/{user_id}/revokeSignInSessions",
                    headers={"Authorization": f"Bearer {token}", "Content-Length": "0"},
                )
                return r.status_code in (200, 204)
        except Exception as exc:
            logger.error("AzureAD revoke sessions failed for %s: %s", user_id, exc)
            return False

    async def reset_password(self, user_id: str, config: dict) -> str:
        """Force a password reset at next sign-in. Returns status message."""
        try:
            token = await self._get_token(config)
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.patch(
                    f"{_GRAPH_BASE}/users/{user_id}",
                    json={"passwordPolicies": "DisablePasswordExpiration", "passwordProfile": {"forceChangePasswordNextSignIn": True}},
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                )
                if r.status_code in (200, 204):
                    return "Password reset flag set — user must change password on next login."
                return f"Failed with status {r.status_code}"
        except Exception as exc:
            logger.error("AzureAD reset password failed for %s: %s", user_id, exc)
            return f"Error: {exc}"

    async def _get_token(self, config: dict) -> str:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{_LOGIN_BASE}/{config['tenant_id']}/oauth2/v2.0/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": config["client_id"],
                    "client_secret": config["client_secret"],
                    "scope": "https://graph.microsoft.com/.default",
                },
            )
            r.raise_for_status()
            return r.json()["access_token"]
