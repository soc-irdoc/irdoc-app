"""
RBAC permission system.

Roles (ascending privilege): viewer < analyst < senior_analyst < admin

Permission boundaries are enforced server-side only — never rely on frontend hiding.
"""
from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user

ROLE_HIERARCHY = {
    "viewer": 0,
    "analyst": 1,
    "senior_analyst": 2,
    "admin": 3,
}

# Permission → minimum required role
PERMISSIONS: dict[str, str] = {
    # Incidents
    "incidents.read": "viewer",
    "incidents.create": "analyst",
    "incidents.update": "analyst",
    "incidents.delete": "senior_analyst",
    "incidents.close": "senior_analyst",
    # Timeline
    "timeline.read": "viewer",
    "timeline.create": "analyst",
    "timeline.update_own": "analyst",
    "timeline.delete_any": "senior_analyst",
    "timeline.pin": "senior_analyst",
    # IOCs
    "iocs.read": "viewer",
    "iocs.create": "analyst",
    "iocs.update": "analyst",
    "iocs.delete": "senior_analyst",
    # Tasks
    "tasks.read": "viewer",
    "tasks.update": "analyst",
    "tasks.create": "analyst",
    "tasks.delete": "senior_analyst",
    # Attachments
    "attachments.read": "viewer",
    "attachments.upload": "analyst",
    "attachments.delete": "senior_analyst",
    # Reports
    "reports.read": "viewer",
    "reports.generate": "viewer",
    # Templates
    "templates.read": "viewer",
    "templates.create": "senior_analyst",
    "templates.update": "senior_analyst",
    "templates.delete": "senior_analyst",
    # Admin
    "users.read": "viewer",
    "users.manage": "admin",
    "api_keys.manage": "admin",
    "integrations.manage": "admin",
    "storage.manage": "admin",
    "audit_log.read": "admin",
    # Assets
    "assets.read": "viewer",
    "assets.create": "analyst",
    "assets.update": "analyst",
    "assets.delete": "senior_analyst",
    # Containment (high-risk)
    "containment.execute": "senior_analyst",
}


def has_permission(user_role: str, permission: str) -> bool:
    required_role = PERMISSIONS.get(permission)
    if required_role is None:
        return False
    return ROLE_HIERARCHY.get(user_role, -1) >= ROLE_HIERARCHY.get(required_role, 99)


def require_permission(permission: str):
    """FastAPI dependency that enforces a permission check."""
    async def _check(current_user=Depends(get_current_user)):
        if not has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: {permission} requires role "
                       f"'{PERMISSIONS.get(permission, 'unknown')}'",
            )
        return current_user
    return _check


def require_role(minimum_role: str):
    """FastAPI dependency that requires at least a minimum role."""
    async def _check(current_user=Depends(get_current_user)):
        if ROLE_HIERARCHY.get(current_user.role, -1) < ROLE_HIERARCHY.get(minimum_role, 99):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{minimum_role}' or higher required",
            )
        return current_user
    return _check
