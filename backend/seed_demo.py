"""
Demo-only seed script — creates the org, the 4 demo role accounts, and ~20
richly-detailed incidents used by the public demo.irdoc.io environment.

This is intentionally NOT wired into entrypoint.sh (unlike seed.py). It must
only ever be invoked explicitly, on the demo box, by docker/demo-restore.sh —
running it against a real customer install would create known-credential
accounts, which is exactly the bug seed.py's docstring warns about. See
seed.py and test_seed.py for the "no known default admin" invariant this
script deliberately sits outside of.

Usage (inside the backend container, after `alembic upgrade head`):
    DEMO_PASSWORD=... python seed_demo.py

Idempotent: if any User already exists, it does nothing (the restore script
is what actually wipes the DB before calling this).
"""
import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.incident import Incident
from app.models.ioc import IOC
from app.models.task import Task
from app.models.template import IncidentTemplate
from app.models.timeline import TimelineEntry
from app.models.user import User
from app.services import auth_service, incident_service

logger = logging.getLogger(__name__)

DEFAULT_PASSWORD = "IrdocDemo2026!"

# Role -> (email, full name, env var override for that role's password)
DEMO_ACCOUNTS = [
    ("admin@irdoc.io", "Demo Admin", "admin", "DEMO_ADMIN_PASSWORD"),
    ("senior_analyst@irdoc.io", "Demo Senior Analyst", "senior_analyst", "DEMO_SENIOR_ANALYST_PASSWORD"),
    ("analyst@irdoc.io", "Demo Analyst", "analyst", "DEMO_ANALYST_PASSWORD"),
    ("viewer@irdoc.io", "Demo Viewer", "viewer", "DEMO_VIEWER_PASSWORD"),
]

# Containment/closure lag, keyed by severity — used to derive contained_at/closed_at
# from opened_at so timestamps read as plausible rather than instantaneous.
_CONTAINMENT_HOURS = {"sev1": 4, "sev2": 8, "sev3": 16, "sev4": 30}
_CLOSURE_HOURS = {"sev1": 24, "sev2": 48, "sev3": 72, "sev4": 120}

# 20 incidents, 5 per system template category, cycling through all 4 statuses
# so every status/category combination is represented at least once.
INCIDENT_SCENARIOS = [
    # ── phishing ─────────────────────────────────────────────────────────────
    {
        "template_slug": "phishing", "status": "open", "severity": "sev1",
        "title": "Executive spear-phishing targeting CFO — fraudulent wire request",
        "summary": "A spoofed email impersonating the CEO asked the CFO to authorize an urgent wire transfer. "
                    "The transfer was not made; the sender domain and email are under investigation.",
        "attack_vector": ["email", "social-engineering"], "affected_users": 1, "days_ago": 1,
        "assigned_role": "senior_analyst",
        "iocs": [("domain", "acme-financeteam.com", "Lookalike domain used as the reply-to address")],
    },
    {
        "template_slug": "phishing", "status": "monitoring", "severity": "sev2",
        "title": "Bulk phishing campaign impersonating IT helpdesk",
        "summary": "34 employees received an email asking them to 'verify their password' via a fake helpdesk portal. "
                    "The malicious link has been blocked; monitoring for any successful credential entry.",
        "attack_vector": ["email"], "affected_users": 34, "days_ago": 3,
        "assigned_role": "analyst",
        "iocs": [("url", "hxxps://it-helpdesk-verify[.]net/login", "Credential harvesting page")],
    },
    {
        "template_slug": "phishing", "status": "contained", "severity": "sev2",
        "title": "Credential-harvesting phishing page mimicking SSO login",
        "summary": "A pixel-perfect clone of the corporate SSO login page was distributed via a QR code in a "
                    "vendor invoice. 12 users clicked through; passwords for affected accounts have been reset.",
        "attack_vector": ["email", "web"], "affected_users": 12, "days_ago": 9,
        "assigned_role": "analyst",
        "iocs": [("domain", "sso-acmecorp-secure.net", "Cloned SSO login page")],
    },
    {
        "template_slug": "phishing", "status": "closed", "severity": "sev3",
        "title": "QR-code phishing ('quishing') via physical mail to finance team",
        "summary": "A physical letter with a malicious QR code was mailed to the finance department. No devices "
                    "were compromised; awareness training was issued to the affected team.",
        "attack_vector": ["physical", "mobile"], "affected_users": 4, "days_ago": 21,
        "assigned_role": "senior_analyst",
        "iocs": [("url", "hxxps://bit.ly/3xQu1sh", "Shortened URL embedded in the QR code")],
    },
    {
        "template_slug": "phishing", "status": "open", "severity": "sev3",
        "title": "Phishing email with malicious OneDrive link reported by employee",
        "summary": "An employee self-reported a suspicious 'shared document' email before clicking. Sender and "
                    "link are being triaged.",
        "attack_vector": ["email"], "affected_users": 1, "days_ago": 0,
        "assigned_role": "analyst",
        "iocs": [("email", "noreply@onedrive-shared-file.com", "Spoofed sender address")],
    },
    # ── credential-compromise ────────────────────────────────────────────────
    {
        "template_slug": "credential-compromise", "status": "monitoring", "severity": "sev1",
        "title": "Leaked credentials from third-party breach reused against VPN",
        "summary": "Credentials exposed in an unrelated third-party breach were used in a successful VPN login. "
                    "The account has been forced to reset; monitoring for further reuse across other services.",
        "attack_vector": ["vpn", "credential-stuffing"], "affected_users": 2, "days_ago": 2,
        "assigned_role": "admin",
        "iocs": [("ip", "203.0.113.44", "Source IP of the VPN login")],
    },
    {
        "template_slug": "credential-compromise", "status": "contained", "severity": "sev1",
        "title": "Service account credentials found in public GitHub repo",
        "summary": "A hardcoded service account credential was discovered in a public fork of an internal tool. "
                    "The credential has been rotated and the repository history scrubbed.",
        "attack_vector": ["source-code-leak"], "affected_users": 1, "days_ago": 6,
        "assigned_role": "senior_analyst",
        "iocs": [("other", "github.com/former-contractor/acme-tool", "Public repo containing the leaked credential")],
    },
    {
        "template_slug": "credential-compromise", "status": "closed", "severity": "sev2",
        "title": "Password-spray attack against Microsoft 365 tenant",
        "summary": "Low-and-slow password-spray attempts were detected against 58 accounts over several days. "
                    "No accounts were compromised; conditional access policies were tightened.",
        "attack_vector": ["password-spray"], "affected_users": 58, "days_ago": 18,
        "assigned_role": "analyst",
        "iocs": [("ip", "198.51.100.23", "Primary source IP for the spray attempts")],
    },
    {
        "template_slug": "credential-compromise", "status": "open", "severity": "sev2",
        "title": "Suspicious OAuth app granted mailbox access via consent phishing",
        "summary": "A user granted a third-party OAuth application broad mailbox permissions after a consent "
                    "phishing prompt. Scope and blast radius are being assessed.",
        "attack_vector": ["oauth", "email"], "affected_users": 3, "days_ago": 1,
        "assigned_role": "senior_analyst",
        "iocs": [("other", "app-id: 7e2c1a9d-...", "Malicious OAuth application ID")],
    },
    {
        "template_slug": "credential-compromise", "status": "monitoring", "severity": "sev3",
        "title": "Former employee account reactivated without authorization",
        "summary": "An offboarded employee's account was found re-enabled outside the normal offboarding "
                    "process. Account has been disabled again; reviewing access logs for activity during the window.",
        "attack_vector": ["insider", "access-control"], "affected_users": 1, "days_ago": 5,
        "assigned_role": "admin",
        "iocs": [],
    },
    # ── malware-infection ────────────────────────────────────────────────────
    {
        "template_slug": "malware-infection", "status": "contained", "severity": "sev3",
        "title": "Cryptomining malware detected on build server",
        "summary": "EDR flagged an unauthorized cryptomining process consuming CPU on a CI build agent. "
                    "The host has been isolated and the process terminated.",
        "attack_vector": ["endpoint"], "affected_users": 1, "days_ago": 11,
        "assigned_role": "analyst",
        "iocs": [("hash", "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08", "Cryptominer binary SHA-256")],
    },
    {
        "template_slug": "malware-infection", "status": "closed", "severity": "sev2",
        "title": "USB-borne worm spreading across warehouse kiosks",
        "summary": "A self-propagating worm spread via USB drives across 7 warehouse kiosk terminals. All "
                    "affected devices were reimaged; USB ports on kiosks are now policy-restricted.",
        "attack_vector": ["removable-media"], "affected_users": 7, "days_ago": 25,
        "assigned_role": "analyst",
        "iocs": [("hash", "1c383cd30b7c298ab50293adfecb7b18", "Worm dropper MD5")],
    },
    {
        "template_slug": "malware-infection", "status": "open", "severity": "sev1",
        "title": "Ransomware note discovered on finance file server",
        "summary": "A ransom note was found on the finance department's file server; several shares show "
                    "encrypted file extensions. The host has been network-isolated pending forensic imaging.",
        "attack_vector": ["endpoint", "lateral-movement"], "affected_users": 1, "days_ago": 0,
        "assigned_role": "admin",
        "iocs": [("ip", "192.0.2.77", "Suspected lateral-movement source host")],
    },
    {
        "template_slug": "malware-infection", "status": "monitoring", "severity": "sev1",
        "title": "Trojanized invoice attachment executed on accounts-payable workstation",
        "summary": "A malicious macro-enabled invoice was opened by an AP clerk, dropping a remote-access trojan. "
                    "The host has been reimaged; monitoring the network for further beaconing.",
        "attack_vector": ["email", "endpoint"], "affected_users": 1, "days_ago": 4,
        "assigned_role": "senior_analyst",
        "iocs": [("domain", "cdn-update-service.net", "Suspected C2 domain")],
    },
    {
        "template_slug": "malware-infection", "status": "contained", "severity": "sev4",
        "title": "Legacy EDR alert: known malware family reappears on retired laptop",
        "summary": "A previously-decommissioned laptop, briefly reconnected for data recovery, triggered an alert "
                    "for a malware family from a prior incident. The device has been wiped again.",
        "attack_vector": ["endpoint"], "affected_users": 1, "days_ago": 14,
        "assigned_role": "analyst",
        "iocs": [],
    },
    # ── suspicious-login ─────────────────────────────────────────────────────
    {
        "template_slug": "suspicious-login", "status": "closed", "severity": "sev3",
        "title": "Brute-force attempts against exposed RDP host",
        "summary": "Thousands of failed RDP login attempts were logged against an internet-facing jump host. "
                    "No successful logins occurred; the host was moved behind the VPN.",
        "attack_vector": ["rdp", "brute-force"], "affected_users": 0, "days_ago": 33,
        "assigned_role": "admin",
        "iocs": [("ip", "203.0.113.201", "Primary brute-force source IP")],
    },
    {
        "template_slug": "suspicious-login", "status": "open", "severity": "sev2",
        "title": "Multiple failed MFA prompts followed by successful login from unrecognized device",
        "summary": "A user received a burst of unexpected MFA push notifications, one of which was accidentally "
                    "approved. Reviewing whether any post-login actions were taken.",
        "attack_vector": ["mfa-fatigue"], "affected_users": 1, "days_ago": 1,
        "assigned_role": "analyst",
        "iocs": [],
    },
    {
        "template_slug": "suspicious-login", "status": "monitoring", "severity": "sev1",
        "title": "After-hours admin console login from unfamiliar ASN",
        "summary": "An administrative console login occurred at 3am local time from an ASN never seen for this "
                    "account. Session was terminated; monitoring for repeat attempts.",
        "attack_vector": ["credential-misuse"], "affected_users": 1, "days_ago": 2,
        "assigned_role": "senior_analyst",
        "iocs": [("ip", "198.51.100.9", "Source IP of the after-hours login")],
    },
    {
        "template_slug": "suspicious-login", "status": "contained", "severity": "sev3",
        "title": "Login from Tor exit node on customer-support shared account",
        "summary": "A shared support-team account was used to log in from a known Tor exit node. The account's "
                    "password has been rotated and Tor egress is now blocked at the WAF.",
        "attack_vector": ["anonymization"], "affected_users": 1, "days_ago": 8,
        "assigned_role": "analyst",
        "iocs": [("ip", "185.220.101.7", "Tor exit node used for the login")],
    },
    {
        "template_slug": "suspicious-login", "status": "closed", "severity": "sev2",
        "title": "Geographically impossible logins across two continents within minutes",
        "summary": "Impossible-travel detection flagged logins from two continents 11 minutes apart on the same "
                    "account. Investigation concluded the account had been compromised via a stale session token, "
                    "which has been revoked.",
        "attack_vector": ["session-hijack"], "affected_users": 2, "days_ago": 16,
        "assigned_role": "senior_analyst",
        "iocs": [("ip", "91.198.174.192", "Second-continent login source")],
    },
]


def _resolve_password(role: str, env_var: str) -> str:
    return os.environ.get(env_var) or os.environ.get("DEMO_PASSWORD") or DEFAULT_PASSWORD


async def _create_demo_users(db) -> dict[str, User]:
    """Creates the org's admin (via perform_setup) plus the other 3 role accounts.

    DEMO_ACCOUNTS lists admin first, so perform_setup's newly-created org_id is
    known before the other three register_user() calls need it.
    """
    users: dict[str, User] = {}
    org_id: str | None = None
    for email, full_name, role, env_var in DEMO_ACCOUNTS:
        password = _resolve_password(role, env_var)
        if role == "admin":
            # The only sanctioned way to create the first user + org.
            user = await auth_service.perform_setup(
                db, email=email, full_name=full_name, password=password, org_name="IRDoc Demo"
            )
            org_id = str(user.org_id)
        else:
            user = await auth_service.register_user(
                db, email=email, full_name=full_name, password=password, org_id=org_id, role=role
            )
        users[role] = user
    return users


async def _create_incident(db, org_id: str, users: dict[str, User], templates: dict[str, IncidentTemplate],
                            scenario: dict) -> None:
    now = datetime.now(UTC)
    opened_at = now - timedelta(days=scenario["days_ago"], hours=6)
    status_ = scenario["status"]
    severity = scenario["severity"]
    template = templates[scenario["template_slug"]]

    contained_at = None
    closed_at = None
    if status_ in ("monitoring", "contained", "closed"):
        contained_at = opened_at + timedelta(hours=_CONTAINMENT_HOURS[severity])
    if status_ == "closed":
        closed_at = contained_at + timedelta(hours=_CLOSURE_HOURS[severity])

    ref = await incident_service.generate_ref(db, org_id)
    assigned_user = users[scenario["assigned_role"]]

    incident = Incident(
        org_id=org_id,
        incident_ref=ref,
        title=scenario["title"],
        severity=severity,
        status=status_,
        template_id=template.id,
        assigned_to=assigned_user.id,
        created_by=users["admin"].id,
        opened_at=opened_at,
        contained_at=contained_at,
        closed_at=closed_at,
        executive_summary=scenario["summary"],
        attack_vector=scenario["attack_vector"],
        affected_users=scenario["affected_users"],
    )
    db.add(incident)
    await db.flush()

    # ── Timeline ─────────────────────────────────────────────────────────────
    db.add(TimelineEntry(
        incident_id=incident.id, author_id=assigned_user.id, entry_type="detection",
        occurred_at=opened_at, description=f"Detected: {scenario['title']}.", source="manual",
    ))
    if status_ in ("monitoring", "contained", "closed"):
        db.add(TimelineEntry(
            incident_id=incident.id, author_id=assigned_user.id, entry_type="analysis",
            occurred_at=opened_at + timedelta(hours=1), description="Initial triage and analysis completed.",
            source="manual",
        ))
        db.add(TimelineEntry(
            incident_id=incident.id, author_id=assigned_user.id, entry_type="containment",
            occurred_at=contained_at, description="Containment actions applied.", source="manual",
        ))
    if status_ == "closed":
        db.add(TimelineEntry(
            incident_id=incident.id, author_id=users["admin"].id, entry_type="note",
            occurred_at=closed_at, description="Incident closed after remediation and lessons-learned review.",
            source="manual",
        ))

    # ── IOCs ─────────────────────────────────────────────────────────────────
    for ioc_type, value, description in scenario["iocs"]:
        db.add(IOC(
            incident_id=incident.id, ioc_type=ioc_type, value=value, description=description,
            confidence=70, status="remediated" if status_ == "closed" else "active",
            added_by=assigned_user.id,
        ))

    # ── Tasks (from the incident's own template) ────────────────────────────
    task_defs = (template.tasks_json or [])[:4]
    for i, task_def in enumerate(task_defs):
        if status_ == "closed":
            task_status, completed_at, completed_by = "done", closed_at, assigned_user.id
        elif status_ == "contained":
            task_status = "done" if i < len(task_defs) - 1 else "in_progress"
            completed_at = contained_at if task_status == "done" else None
            completed_by = assigned_user.id if task_status == "done" else None
        elif status_ == "monitoring":
            task_status = "done" if i == 0 else ("in_progress" if i == 1 else "pending")
            completed_at = opened_at + timedelta(hours=1) if task_status == "done" else None
            completed_by = assigned_user.id if task_status == "done" else None
        else:  # open
            task_status = "in_progress" if i == 0 else "pending"
            completed_at = None
            completed_by = None

        db.add(Task(
            incident_id=incident.id, template_id=template.id, title=task_def["title"],
            phase=task_def.get("phase"), priority=task_def.get("priority", "medium"),
            status=task_status, assigned_to=assigned_user.id,
            completed_at=completed_at, completed_by=completed_by, sort_order=i,
        ))


async def seed_demo() -> None:
    async with AsyncSessionLocal() as db:
        if await auth_service.setup_complete(db):
            logger.info("seed_demo: users already exist, skipping (restore script should wipe the DB first).")
            return

        logger.info("seed_demo: creating demo org, users, and incidents...")

        users = await _create_demo_users(db)
        org_id = str(users["admin"].org_id)

        templates_result = await db.execute(select(IncidentTemplate).where(IncidentTemplate.is_system.is_(True)))
        templates = {t.slug: t for t in templates_result.scalars().all()}
        missing = {s["template_slug"] for s in INCIDENT_SCENARIOS} - set(templates)
        if missing:
            raise RuntimeError(
                f"seed_demo: system incident templates {missing} not found — run seed.py first."
            )

        for scenario in INCIDENT_SCENARIOS:
            await _create_incident(db, org_id, users, templates, scenario)

        await db.commit()
        logger.info(
            "seed_demo: done. Created %d users and %d incidents.",
            len(users), len(INCIDENT_SCENARIOS),
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_demo())
