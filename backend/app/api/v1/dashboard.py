"""Dashboard stats endpoint — aggregated metrics for the overview page."""
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.audit import AuditLog
from app.models.incident import Incident
from app.models.integration import OrgIntegration
from app.models.task import Task
from app.models.user import User
from app.models.user_invite import UserInvite

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    from_dt: datetime | None = Query(None),
    to_dt: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    now = datetime.now(timezone.utc)
    effective_to = to_dt or now
    effective_from = from_dt or (now - timedelta(days=7))

    # ── Incidents by status ──────────────────────────────────────────────────
    status_rows = (await db.execute(
        select(Incident.status, func.count().label("n"))
        .where(
            Incident.org_id == current_user.org_id,
            Incident.created_at.between(effective_from, effective_to),
        )
        .group_by(Incident.status)
    )).all()
    by_status = {r.status: r.n for r in status_rows}

    # ── Incidents by severity ────────────────────────────────────────────────
    sev_rows = (await db.execute(
        select(Incident.severity, func.count().label("n"))
        .where(
            Incident.org_id == current_user.org_id,
            Incident.created_at.between(effective_from, effective_to),
        )
        .group_by(Incident.severity)
    )).all()
    by_severity = {r.severity: r.n for r in sev_rows}

    # ── Recent incidents (8 most recent, all time) ───────────────────────────
    recent_rows = (await db.execute(
        select(Incident)
        .where(Incident.org_id == current_user.org_id)
        .options(selectinload(Incident.assigned_user))
        .order_by(Incident.created_at.desc())
        .limit(8)
    )).scalars().all()

    # ── Team workload: open cases per analyst ────────────────────────────────
    workload_rows = (await db.execute(
        select(
            User.id,
            User.full_name,
            User.avatar_initials,
            func.count(Incident.id).label("open_count"),
        )
        .join(Incident, Incident.assigned_to == User.id)
        .where(
            User.org_id == current_user.org_id,
            Incident.status.in_(["open", "monitoring", "contained"]),
        )
        .group_by(User.id, User.full_name, User.avatar_initials)
        .order_by(func.count(Incident.id).desc())
    )).all()

    # ── Resolved count in time range ─────────────────────────────────────────
    resolved_count: int = (await db.execute(
        select(func.count())
        .select_from(Incident)
        .where(
            Incident.org_id == current_user.org_id,
            Incident.status == "closed",
            Incident.closed_at.between(effective_from, effective_to),
        )
    )).scalar_one()

    result: dict[str, Any] = {
        "incidents": {
            "by_status": {k: by_status.get(k, 0) for k in ["open", "monitoring", "contained", "closed"]},
            "by_severity": {k: by_severity.get(k, 0) for k in ["sev1", "sev2", "sev3", "sev4"]},
            "total": sum(by_status.values()),
            "recent": [_serialize_incident(i) for i in recent_rows],
        },
        "team_workload": [
            {
                "user_id": str(r.id),
                "full_name": r.full_name,
                "avatar_initials": r.avatar_initials or "",
                "open_count": r.open_count,
            }
            for r in workload_rows
        ],
        "resolved_count": resolved_count,
    }

    # ── analyst + senior_analyst: personal stats ─────────────────────────────
    if current_user.role in ("analyst", "senior_analyst"):
        assigned_count: int = (await db.execute(
            select(func.count())
            .select_from(Incident)
            .where(
                Incident.org_id == current_user.org_id,
                Incident.assigned_to == current_user.id,
                Incident.status.in_(["open", "monitoring", "contained"]),
            )
        )).scalar_one()

        pending_tasks: int = (await db.execute(
            select(func.count())
            .select_from(Task)
            .join(Incident, Task.incident_id == Incident.id)
            .where(
                Incident.org_id == current_user.org_id,
                Task.assigned_to == current_user.id,
                Task.status != "completed",
            )
        )).scalar_one()

        recent_task_rows = (await db.execute(
            select(Task.id, Task.title, Task.priority, Task.incident_id, Incident.incident_ref)
            .join(Incident, Task.incident_id == Incident.id)
            .where(
                Incident.org_id == current_user.org_id,
                Task.assigned_to == current_user.id,
                Task.status != "completed",
            )
            .order_by(Task.created_at.desc())
            .limit(5)
        )).all()

        result["my_stats"] = {
            "assigned_count": assigned_count,
            "pending_tasks": pending_tasks,
            "recent_tasks": [
                {
                    "id": str(r.id),
                    "title": r.title,
                    "priority": r.priority,
                    "incident_id": str(r.incident_id),
                    "incident_ref": r.incident_ref,
                }
                for r in recent_task_rows
            ],
        }

    # ── senior_analyst: led cases overview ───────────────────────────────────
    if current_user.role == "senior_analyst":
        led_count: int = (await db.execute(
            select(func.count())
            .select_from(Incident)
            .where(
                Incident.org_id == current_user.org_id,
                Incident.assigned_to == current_user.id,
                Incident.status.in_(["open", "monitoring", "contained"]),
            )
        )).scalar_one()

        unassigned_count: int = (await db.execute(
            select(func.count())
            .select_from(Incident)
            .where(
                Incident.org_id == current_user.org_id,
                Incident.assigned_to.is_(None),
                Incident.status.in_(["open", "monitoring", "contained"]),
            )
        )).scalar_one()

        led_recent_rows = (await db.execute(
            select(Incident)
            .where(
                Incident.org_id == current_user.org_id,
                Incident.assigned_to == current_user.id,
                Incident.status.in_(["open", "monitoring", "contained"]),
            )
            .order_by(Incident.created_at.desc())
            .limit(3)
        )).scalars().all()

        result["led_cases"] = {
            "count": led_count,
            "unassigned_count": unassigned_count,
            "recent": [
                {
                    "id": str(i.id),
                    "incident_ref": i.incident_ref,
                    "title": i.title,
                    "severity": i.severity,
                }
                for i in led_recent_rows
            ],
        }

    # ── viewer: top attack vectors ────────────────────────────────────────────
    if current_user.role == "viewer":
        vector_rows = (await db.execute(
            text(
                "SELECT unnest(attack_vector) AS v, COUNT(*) AS n "
                "FROM incidents "
                "WHERE org_id = :org_id "
                "  AND created_at BETWEEN :from_dt AND :to_dt "
                "  AND cardinality(attack_vector) > 0 "
                "GROUP BY v ORDER BY n DESC LIMIT 5"
            ),
            {
                "org_id": str(current_user.org_id),
                "from_dt": effective_from,
                "to_dt": effective_to,
            },
        )).all()
        result["attack_vectors"] = [
            {"vector": r.v, "count": r.n} for r in vector_rows if r.v
        ]

    # ── admin: org health + user activity ────────────────────────────────────
    if current_user.role == "admin":
        active_users: int = (await db.execute(
            select(func.count())
            .select_from(User)
            .where(User.org_id == current_user.org_id, User.is_active.is_(True))
        )).scalar_one()

        mfa_count: int = (await db.execute(
            select(func.count())
            .select_from(User)
            .where(
                User.org_id == current_user.org_id,
                User.is_active.is_(True),
                User.mfa_enabled.is_(True),
            )
        )).scalar_one()

        pending_invites: int = (await db.execute(
            select(func.count())
            .select_from(UserInvite)
            .where(
                UserInvite.org_id == current_user.org_id,
                UserInvite.accepted_at.is_(None),
                UserInvite.expires_at > datetime.now(timezone.utc),
            )
        )).scalar_one()

        total_integrations: int = (await db.execute(
            select(func.count())
            .select_from(OrgIntegration)
            .where(OrgIntegration.org_id == current_user.org_id)
        )).scalar_one()

        active_integrations: int = (await db.execute(
            select(func.count())
            .select_from(OrgIntegration)
            .where(
                OrgIntegration.org_id == current_user.org_id,
                OrgIntegration.is_enabled.is_(True),
            )
        )).scalar_one()

        audit_rows = (await db.execute(
            select(
                AuditLog.action,
                AuditLog.entity_type,
                AuditLog.created_at,
                User.email.label("user_email"),
            )
            .outerjoin(User, AuditLog.user_id == User.id)
            .where(AuditLog.org_id == current_user.org_id)
            .order_by(AuditLog.created_at.desc())
            .limit(5)
        )).all()

        result["org_health"] = {
            "active_users": active_users,
            "mfa_enabled_count": mfa_count,
            "pending_invites": pending_invites,
            "total_integrations": total_integrations,
            "active_integrations": active_integrations,
        }
        result["recent_audit"] = [
            {
                "action": r.action,
                "entity_type": r.entity_type or "",
                "created_at": r.created_at.isoformat(),
                "user_email": r.user_email or "system",
            }
            for r in audit_rows
        ]

    return {"data": result, "error": None}


def _serialize_incident(inc: Incident) -> dict:
    assigned = None
    if inc.assigned_user:
        assigned = {
            "id": str(inc.assigned_user.id),
            "full_name": inc.assigned_user.full_name,
            "avatar_initials": inc.assigned_user.avatar_initials or "",
        }
    return {
        "id": str(inc.id),
        "incident_ref": inc.incident_ref,
        "title": inc.title,
        "severity": inc.severity,
        "status": inc.status,
        "created_at": inc.created_at.isoformat(),
        "assigned_user": assigned,
    }
