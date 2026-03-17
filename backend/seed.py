"""
Seed script — runs on first startup if DB is empty.
Creates: default org, admin user, 4 system incident templates, 3 system report templates.
"""
import asyncio
import logging

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.organization import Organization
from app.models.template import IncidentTemplate, ReportTemplate
from app.models.user import User

logger = logging.getLogger(__name__)

# ─── System Incident Templates ─────────────────────────────────────────────────

INCIDENT_TEMPLATES = [
    {
        "name": "Phishing Attack",
        "slug": "phishing",
        "description": "Credential theft via phishing email",
        "tasks_json": [
            {"title": "Identify phishing email and recipients", "phase": "Detection", "priority": "critical"},
            {"title": "Preserve original email headers and attachments", "phase": "Detection", "priority": "high"},
            {"title": "Block sender domain/IP at email gateway", "phase": "Containment", "priority": "critical"},
            {"title": "Reset credentials for affected users", "phase": "Containment", "priority": "critical"},
            {"title": "Enable MFA for affected accounts", "phase": "Containment", "priority": "high"},
            {"title": "Check for additional mailbox rules / forwarding", "phase": "Analysis", "priority": "high"},
            {"title": "Review sign-in logs for affected accounts", "phase": "Analysis", "priority": "high"},
            {"title": "Notify affected users", "phase": "Communication", "priority": "medium"},
            {"title": "Submit phishing report to email provider", "phase": "Remediation", "priority": "low"},
            {"title": "Update phishing awareness training", "phase": "Post-Incident", "priority": "low"},
        ],
    },
    {
        "name": "Credential Compromise",
        "slug": "credential-compromise",
        "description": "Account takeover or credential theft",
        "tasks_json": [
            {"title": "Identify compromised account(s)", "phase": "Detection", "priority": "critical"},
            {"title": "Revoke active sessions and tokens", "phase": "Containment", "priority": "critical"},
            {"title": "Force password reset", "phase": "Containment", "priority": "critical"},
            {"title": "Enable MFA immediately", "phase": "Containment", "priority": "critical"},
            {"title": "Review access logs for lateral movement", "phase": "Analysis", "priority": "high"},
            {"title": "Check for new admin accounts or backdoors", "phase": "Analysis", "priority": "high"},
            {"title": "Identify breach vector (phishing, brute force, etc.)", "phase": "Analysis", "priority": "high"},
            {"title": "Audit permissions — remove excessive access", "phase": "Remediation", "priority": "medium"},
            {"title": "Notify user and management", "phase": "Communication", "priority": "medium"},
            {"title": "Review and strengthen password policy", "phase": "Post-Incident", "priority": "low"},
        ],
    },
    {
        "name": "Malware Infection",
        "slug": "malware-infection",
        "description": "Endpoint compromise by malware or ransomware",
        "tasks_json": [
            {"title": "Identify infected host(s)", "phase": "Detection", "priority": "critical"},
            {"title": "Isolate host from network", "phase": "Containment", "priority": "critical"},
            {"title": "Preserve forensic image of infected system", "phase": "Evidence", "priority": "high"},
            {"title": "Collect memory dump", "phase": "Evidence", "priority": "high"},
            {"title": "Identify malware family and IOCs", "phase": "Analysis", "priority": "high"},
            {"title": "Check for lateral movement to other hosts", "phase": "Analysis", "priority": "critical"},
            {"title": "Review network traffic logs for C2 communication", "phase": "Analysis", "priority": "high"},
            {"title": "Block C2 IPs/domains at firewall", "phase": "Containment", "priority": "critical"},
            {"title": "Rebuild affected host from clean image", "phase": "Remediation", "priority": "high"},
            {"title": "Update AV signatures and EDR rules", "phase": "Remediation", "priority": "medium"},
            {"title": "Deploy all security patches to environment", "phase": "Post-Incident", "priority": "medium"},
        ],
    },
    {
        "name": "Suspicious Login",
        "slug": "suspicious-login",
        "description": "Anomalous authentication activity",
        "tasks_json": [
            {"title": "Review authentication logs for anomalies", "phase": "Detection", "priority": "high"},
            {"title": "Geolocate source IP(s)", "phase": "Analysis", "priority": "high"},
            {"title": "Check if login was successful", "phase": "Analysis", "priority": "critical"},
            {"title": "Contact user to verify activity", "phase": "Analysis", "priority": "high"},
            {"title": "Terminate suspicious sessions if unverified", "phase": "Containment", "priority": "critical"},
            {"title": "Block source IP at firewall/WAF", "phase": "Containment", "priority": "high"},
            {"title": "Enable MFA on account if not already active", "phase": "Containment", "priority": "high"},
            {"title": "Review all recent actions taken by the account", "phase": "Analysis", "priority": "medium"},
            {"title": "Document findings and close", "phase": "Post-Incident", "priority": "low"},
        ],
    },
]

# ─── System Report Templates ───────────────────────────────────────────────────

REPORT_TEMPLATES = [
    {
        "name": "Management Brief",
        "destination": "management",
        "description": "Executive-level summary for non-technical stakeholders",
        "is_default": True,
        "schema_json": [
            {"type": "cover", "title_field": "incident_ref", "subtitle_field": "title"},
            {"type": "section", "title": "Executive Summary", "content_field": "executive_summary"},
            {"type": "stat_row", "fields": ["severity", "status", "affected_users", "duration"]},
            {"type": "ioc_table", "filter": "status=active", "columns": ["type", "value", "status"]},
            {"type": "section", "title": "Containment Actions"},
            {"type": "timeline", "filter": "type=containment", "max_entries": 10},
            {"type": "section", "title": "Recommendations"},
            {"type": "text_block", "content_field": "recommendations"},
        ],
    },
    {
        "name": "Technical Report",
        "destination": "analyst",
        "description": "Full technical details for SOC and IR engineers",
        "is_default": False,
        "schema_json": [
            {"type": "cover", "title_field": "incident_ref", "subtitle_field": "title"},
            {"type": "stat_row", "fields": ["severity", "status", "affected_users", "duration", "attack_vector"]},
            {"type": "section", "title": "Incident Timeline"},
            {"type": "timeline", "filter": "all", "max_entries": 500},
            {"type": "section", "title": "Indicators of Compromise"},
            {"type": "ioc_table", "filter": "all", "columns": ["type", "value", "confidence", "status"]},
            {"type": "section", "title": "Evidence Register"},
            {"type": "evidence_register", "fields": ["filename", "sha256", "uploaded_by", "created_at"]},
            {"type": "section", "title": "Task Checklist"},
            {"type": "task_list", "filter": "all"},
        ],
    },
    {
        "name": "Legal / Compliance Report",
        "destination": "legal",
        "description": "Regulatory and legal review template",
        "is_default": False,
        "schema_json": [
            {"type": "cover", "title_field": "incident_ref", "subtitle_field": "title"},
            {"type": "section", "title": "Incident Overview"},
            {"type": "stat_row", "fields": ["severity", "status", "opened_at", "closed_at", "affected_users"]},
            {"type": "section", "title": "Executive Summary", "content_field": "executive_summary"},
            {"type": "section", "title": "Detection Timeline"},
            {"type": "timeline", "filter": "type=detection", "max_entries": 50},
            {"type": "section", "title": "Response Timeline"},
            {"type": "timeline", "filter": "type=containment", "max_entries": 50},
            {"type": "section", "title": "Data Affected"},
            {"type": "text_block", "placeholder": "Document affected data categories and volume here."},
            {"type": "section", "title": "Regulatory Notifications"},
            {"type": "text_block", "placeholder": "List required regulatory notifications (GDPR, HIPAA, etc.) and status."},
            {"type": "divider"},
            {"type": "text_block", "content": "CONFIDENTIAL — LEGAL PRIVILEGE"},
        ],
    },
]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        # Check if already seeded
        result = await db.execute(select(Organization).where(Organization.slug == "default"))
        if result.scalar_one_or_none():
            logger.info("Seed: already seeded, skipping.")
            return

        logger.info("Seed: seeding database...")

        # 1. Default organization
        org = Organization(name="Default Organization", slug="default", plan="core")
        db.add(org)
        await db.flush()

        # 2. Admin user (force password reset on first login)
        admin = User(
            org_id=org.id,
            email="admin@localhost",
            full_name="IRDoc Admin",
            role="admin",
            password_hash=hash_password("ChangeMe123!"),
            avatar_initials="IA",
            must_reset_password=True,
        )
        db.add(admin)
        await db.flush()

        # 3. System incident templates
        for tmpl_data in INCIDENT_TEMPLATES:
            tmpl = IncidentTemplate(
                org_id=None,  # system template
                name=tmpl_data["name"],
                slug=tmpl_data["slug"],
                description=tmpl_data["description"],
                is_system=True,
                tasks_json=tmpl_data["tasks_json"],
            )
            db.add(tmpl)

        # 4. System report templates
        for rt_data in REPORT_TEMPLATES:
            rt = ReportTemplate(
                org_id=None,  # system template
                name=rt_data["name"],
                destination=rt_data["destination"],
                description=rt_data["description"],
                is_system=True,
                is_default=rt_data.get("is_default", False),
                schema_json=rt_data["schema_json"],
            )
            db.add(rt)

        await db.commit()
        logger.info(
            "Seed: done. Admin user: admin@localhost / ChangeMe123! (must change on first login)"
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed())
