# IRP Phase 5 — Multi-Tenancy, User Management, Enterprise Features & Cloud Storage

> **Status:** Planning  
> **Depends on:** Phase 4 complete  
> **Estimated effort:** 4–5 weeks  
> **Goal:** The platform is ready for organizations with multiple analysts, strict access controls, SSO, full audit logging, and cloud storage backends. This phase unlocks the enterprise licensing tier. Cloud storage backends (S3, Azure Blob, GCS) are implemented here — the abstraction was built in Phase 1, now the cloud adapters are wired and the admin UI is built.

---

## 1. Objectives

By end of Phase 5:
- RBAC: multiple roles with enforced permissions at API and UI level
- User invite system (email-based, role-assigned)
- SSO / SAML 2.0 (premium)
- Full audit log (who did what, when, to what)
- Custom incident templates (org-specific template builder)
- MSSP mode: multiple isolated organizations per deployment
- Cloud storage backends fully implemented: S3, Azure Blob, GCS — admin-configurable with test connection
- Admin panel: team management, org settings, license, storage config, audit log

---

## 2. Role-Based Access Control (RBAC)

### 2.1 Roles

| Role | Description |
|---|---|
| **Admin** | Full access to all features, users, settings, integrations, audit log |
| **Senior Analyst** | All analyst permissions + delete any entry, close incidents, manage templates |
| **Analyst** | Create/edit incidents and their own entries. Cannot delete others' work |
| **Viewer** | Read-only access to all incidents. Cannot add or modify anything |
| **MSSP Admin** | (MSSP mode) Create and manage client organizations |

### 2.2 Permission Matrix

| Action | Admin | Sr. Analyst | Analyst | Viewer |
|---|---|---|---|---|
| View all incidents | ✅ | ✅ | ✅ | ✅ |
| Create incident | ✅ | ✅ | ✅ | ❌ |
| Add timeline entry | ✅ | ✅ | ✅ | ❌ |
| Edit own timeline entry | ✅ | ✅ | ✅ | ❌ |
| Edit any timeline entry | ✅ | ✅ | ❌ | ❌ |
| Delete any entry | ✅ | ✅ | ❌ | ❌ |
| Add/edit IOC | ✅ | ✅ | ✅ | ❌ |
| Close incident | ✅ | ✅ | ❌ | ❌ |
| Generate report | ✅ | ✅ | ✅ | ✅ |
| Manage report templates | ✅ | ✅ | ❌ | ❌ |
| Manage sync policies | ✅ | ✅ | ❌ | ❌ |
| Manage integrations | ✅ | ❌ | ❌ | ❌ |
| Containment actions (revoke, contain) | ✅ | ✅ | ❌ | ❌ |
| Manage users | ✅ | ❌ | ❌ | ❌ |
| Manage API keys | ✅ | ❌ | ❌ | ❌ |
| Configure storage | ✅ | ❌ | ❌ | ❌ |
| View audit log | ✅ | ❌ | ❌ | ❌ |

### 2.3 FastAPI Permission Dependencies

```python
# app/core/permissions.py

ROLE_HIERARCHY = {"admin": 4, "senior_analyst": 3, "analyst": 2, "viewer": 1}

PERMISSION_MAP = {
    "timeline.delete_any":         ["admin", "senior_analyst"],
    "incident.close":              ["admin", "senior_analyst"],
    "templates.manage":            ["admin", "senior_analyst"],
    "integrations.manage":         ["admin"],
    "users.manage":                ["admin"],
    "api_keys.manage":             ["admin"],
    "storage.manage":              ["admin"],
    "audit_log.read":              ["admin"],
    "containment.action":          ["admin", "senior_analyst"],
}

def require_permission(permission: str):
    async def check(user: User = Depends(get_current_user)):
        allowed_roles = PERMISSION_MAP.get(permission, [])
        if user.role not in allowed_roles:
            raise HTTPException(403, f"Permission denied: {permission}")
        return user
    return Depends(check)
```

---

## 3. User Invitation System

### 3.1 Flow

```
Admin → /admin/team → "Invite User"
  → Modal: email address, role selector
  → POST /api/v1/users/invite { email, role }
  → Backend creates UserInvite row (UUID token, 48h expiry)
  → Sends invitation email via configured email backend

Invitee receives email: "You've been invited to IRDoc by [Admin Name]"
  → Clicks link: https://app.company.com/invite/{token}
  → GET /api/v1/users/invite/{token} validates token
  → Shows registration form: name + password (email pre-filled, read-only)
  → POST /api/v1/users/invite/{token}/accept
  → Creates user, assigns role, expires token
  → Auto-login, redirect to /incidents
```

```sql
CREATE TABLE user_invites (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID REFERENCES organizations(id),
    invited_by  UUID REFERENCES users(id),
    email       TEXT NOT NULL,
    role        TEXT NOT NULL,
    token       TEXT UNIQUE NOT NULL,    -- secrets.token_urlsafe(32)
    accepted_at TIMESTAMPTZ,
    expires_at  TIMESTAMPTZ NOT NULL,    -- now() + 48 hours
    created_at  TIMESTAMPTZ DEFAULT now()
);
```

---

## 4. Audit Log (Premium)

Every write action in the system is recorded. Critical for SOC 2, ISO 27001, GDPR investigations, and any legal proceedings involving incident data.

### 4.1 Events Tracked

```python
# All service-layer writes call audit_service.log(...)

AUDIT_EVENTS = [
    # Incidents
    "incident.created", "incident.updated", "incident.closed", "incident.deleted",
    "incident.external_ref.added",

    # Timeline
    "timeline.entry.added", "timeline.entry.updated", "timeline.entry.deleted",
    "timeline.entry.pinned",

    # IOCs
    "ioc.added", "ioc.updated", "ioc.deleted", "ioc.bulk_imported",

    # Tasks
    "task.completed", "task.reopened", "task.assigned",

    # Attachments
    "attachment.uploaded", "attachment.deleted",

    # Reports
    "report.generated", "report.downloaded", "report.deleted",
    "report_template.created", "report_template.updated", "report_template.deleted",

    # Sync
    "sync_policy.created", "sync_policy.triggered", "sync_policy.completed", "sync_policy.failed",

    # Users
    "user.invited", "user.created", "user.role_changed", "user.deactivated", "user.login",
    "user.login_failed", "user.password_changed",

    # API Keys
    "api_key.created", "api_key.used", "api_key.revoked",

    # Integrations
    "integration.enabled", "integration.disabled", "integration.configured",

    # Containment (high visibility)
    "containment.host_isolated",           # CrowdStrike
    "containment.sessions_revoked",        # Azure AD
    "containment.password_reset",          # Azure AD
    "containment.email_quarantined",       # Proofpoint
]
```

### 4.2 Audit Log API

```python
# GET /api/v1/audit-log?org_id=...&user_id=...&action=...&incident_id=...
#   &from=2026-03-01&to=2026-03-31&page=1&per_page=50
```

### 4.3 Audit Log UI

```
AUDIT LOG                                         Filter ▾    Export CSV

2026-03-15 11:32  john.doe@co    timeline.entry.added   INC-2026-0315
                  "Detection entry: Phishing email from support-secure-..."
                  IP: 192.168.1.10  |  Chrome/Win11

2026-03-15 11:15  jane.smith@co  containment.sessions_revoked  INC-2026-0315
                  ⚠️  HIGH RISK  User: finance.user@company.com
                  Confirmed by: Jane Smith (Senior Analyst)

2026-03-15 10:45  API Key: SDP   incident.created       INC-2026-0315
                  Via: ServiceDesk Plus  External ref: SDP-2026-4421
```

Containment actions shown with `⚠️ HIGH RISK` indicator. API-key-initiated actions show the key name instead of a user.

---

## 5. SSO / SAML 2.0 (Premium)

### 5.1 Supported Identity Providers

- Azure AD / Entra ID
- Okta
- Google Workspace
- Any SAML 2.0 compliant IdP

### 5.2 Library

`python3-saml` — battle-tested, used by Salesforce and many enterprise products.

### 5.3 Flow

```
1. User visits /login → "Sign in with SSO" button (if SSO configured for org)
2. Redirect to IdP with SAML AuthnRequest
3. User authenticates at IdP
4. IdP redirects to /auth/saml/acs with SAML Response
5. Backend validates assertion (signature, timing, audience)
6. Extracts: email, full_name, groups
7. Maps IdP group → IRDoc role (configurable in admin panel)
8. Creates or updates User record (email is the stable identifier)
9. Issues JWT access token + refresh cookie as normal
10. User is redirected to /incidents
```

### 5.4 SSO Admin Configuration UI

```
SSO / SAML Configuration                              [PREMIUM]

Identity Provider:  [Azure AD ▾]

Auto-configuration:
  IdP Metadata URL: [https://login.microsoftonline.com/{tenant}/federationmetadata/...]
  [Load Metadata]  ← fetches and fills fields below automatically

Manual configuration (auto-filled from metadata):
  Entity ID:           [https://sts.windows.net/{tenant}/]
  SSO URL:             [https://login.microsoftonline.com/...]
  Certificate:         [paste X.509 certificate]

Attribute Mapping:
  Email field:         [http://schemas.xmlsoap.org/ws/2005/.../emailaddress]
  Name field:          [http://schemas.xmlsoap.org/ws/2005/.../name]
  Groups field:        [http://schemas.microsoft.com/.../groups]

Role Mapping (IdP group → IRDoc role):
  [+ Add mapping]
  SOC-Tier3          →  [Admin          ▾]
  SOC-Analysts       →  [Analyst        ▾]
  IT-Security-View   →  [Viewer         ▾]

SP Metadata (give this to your IdP):
  Entity ID:   https://irpdoc.company.com/auth/saml/metadata
  ACS URL:     https://irpdoc.company.com/auth/saml/acs
  [Download SP Metadata XML]
```

---

## 6. Cloud Storage Backends (Full Implementation)

The `StorageBackend` protocol was defined in Phase 1, and `LocalStorageBackend` was implemented. This phase delivers the cloud adapters and the admin configuration UI.

### 6.1 S3StorageBackend (covers AWS S3, MinIO, Cloudflare R2, Wasabi)

```python
# app/services/storage/s3.py
import boto3
from botocore.exceptions import ClientError

class S3StorageBackend:
    backend_name = "s3"

    def __init__(self, config: dict):
        self.client = boto3.client(
            "s3",
            endpoint_url=config.get("endpoint_url"),       # None = AWS, or MinIO/R2 URL
            aws_access_key_id=config["access_key_id"],
            aws_secret_access_key=config["secret_access_key"],
            region_name=config.get("region", "us-east-1")
        )
        self.bucket = config["bucket"]

    async def store(self, data: bytes, path: str) -> str:
        self.client.put_object(Bucket=self.bucket, Key=path, Body=data)
        return path

    async def get_url(self, path: str, expires_in: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": path},
            ExpiresIn=expires_in
        )

    async def test_connection(self) -> bool:
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except ClientError:
            return False
```

### 6.2 AzureBlobStorageBackend

```python
# app/services/storage/azure_blob.py
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

class AzureBlobStorageBackend:
    backend_name = "azure_blob"

    def __init__(self, config: dict):
        self.client = BlobServiceClient(
            account_url=f"https://{config['account_name']}.blob.core.windows.net",
            credential=config["account_key"]
        )
        self.container = config["container_name"]

    async def get_url(self, path: str, expires_in: int = 3600) -> str:
        sas = generate_blob_sas(
            account_name=..., container_name=self.container, blob_name=path,
            account_key=..., permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(seconds=expires_in)
        )
        return f"https://{account_name}.blob.core.windows.net/{self.container}/{path}?{sas}"
```

### 6.3 GCSStorageBackend

```python
# app/services/storage/gcs.py
from google.cloud import storage as gcs

class GCSStorageBackend:
    backend_name = "gcs"

    def __init__(self, config: dict):
        self.client = gcs.Client.from_service_account_info(json.loads(config["service_account_json"]))
        self.bucket = self.client.bucket(config["bucket_name"])

    async def get_url(self, path: str, expires_in: int = 3600) -> str:
        blob = self.bucket.blob(path)
        return blob.generate_signed_url(expiration=timedelta(seconds=expires_in))
```

### 6.4 Storage Admin Configuration UI

In `/admin` → Storage:

```
STORAGE BACKEND                                    [PREMIUM for cloud backends]

Active Backend:  ● Local Storage  ○ Amazon S3  ○ Azure Blob  ○ Google Cloud Storage

──────────────────────────────────────────────────────────────
 ○  Amazon S3 / S3-Compatible                     [PREMIUM]
    Covers: AWS S3 · MinIO · Cloudflare R2 · Wasabi

    Endpoint URL:     [https://s3.amazonaws.com   ] (leave blank for AWS)
    Access Key ID:    [AKIAIOSFODNN7EXAMPLE       ]
    Secret Access Key:[••••••••••••••••••••••••••  ]
    Bucket:           [irpdoc-evidence             ]
    Region:           [us-east-1                   ]

    [Test Connection ✓]       [Save & Switch]
──────────────────────────────────────────────────────────────
 ○  Azure Blob Storage                             [PREMIUM]
    Account Name:     [mysocteam                  ]
    Account Key:      [••••••••••••••••••••        ]
    Container:        [irp-evidence               ]

    [Test Connection]         [Save & Switch]
──────────────────────────────────────────────────────────────
 ○  Google Cloud Storage                           [PREMIUM]
    Service Account JSON:  [Upload JSON key file  ]
    Bucket:           [irpdoc-evidence             ]

    [Test Connection]         [Save & Switch]
──────────────────────────────────────────────────────────────

Current storage usage:  2.4 GB  (1,847 files)
Forensic integrity:     All files hashed ✓  (SHA-256 stored in database)

⚠️ Migration Note: Switching backends does not move existing files. Existing
attachments remain accessible — their signed URLs are issued by the backend
they were originally uploaded to. New uploads go to the new backend.
New files use the new backend immediately.
```

**SHA-256 independence note** must be visible in the UI: changing the storage backend has zero effect on forensic integrity because hashes live in PostgreSQL, not in the file storage system.

### 6.5 Storage Configuration API

| Method | Path | Description |
|---|---|---|
| GET    | `/admin/storage` | Current config (redacted credentials) + usage stats |
| PUT    | `/admin/storage` | Update backend config |
| POST   | `/admin/storage/test` | Test connection with provided config |
| POST   | `/admin/storage/switch` | Commit and activate new backend |

---

## 7. MSSP Mode (Premium — Enterprise)

For MSSPs managing IR documentation for multiple client organizations.

### 7.1 Architecture

```
MSSP Deployment
├── Organization: MSSP-Internal     (the MSSP's own incidents)
├── Organization: Client-A          (Client A's incidents — fully isolated)
├── Organization: Client-B
└── Organization: Client-C
```

Each client org is fully isolated: separate incidents, separate integrations, separate users, separate storage config, separate report templates.

### 7.2 Row-Level Security

```sql
ALTER TABLE incidents         ENABLE ROW LEVEL SECURITY;
ALTER TABLE timeline_entries  ENABLE ROW LEVEL SECURITY;
ALTER TABLE iocs              ENABLE ROW LEVEL SECURITY;
ALTER TABLE attachments       ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks             ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports           ENABLE ROW LEVEL SECURITY;

CREATE POLICY org_isolation ON incidents
    USING (org_id = current_setting('app.current_org_id')::uuid);
-- Repeated for each table
```

The backend middleware sets `app.current_org_id` at the start of every request from the authenticated user's org. This is a database-level guarantee — even a bug in application code cannot leak cross-org data.

### 7.3 MSSP Admin Capabilities

- Create/archive/suspend client organizations
- Assign MSSP analysts to specific client orgs (multi-org users)
- Cross-org dashboard: "8 open incidents across 5 clients"
- Per-client monthly report generation
- Per-client custom branding (logo, colors — custom branding premium feature)

---

## 8. Custom Incident Template Builder

Org admins can create their own incident templates beyond the 4 system defaults.

### 8.1 Template Builder UI

```
INCIDENT TEMPLATES                               [+ New Template]

System Templates (read-only — clone to customise):
  Phishing Investigation         [Clone]
  Credential Compromise          [Clone]
  Malware Infection              [Clone]
  Suspicious Login               [Clone]

Organisation Templates:
  Ransomware Response            [Edit] [Clone] [Delete]
  Insider Threat Investigation   [Edit] [Clone] [Delete]
```

**Edit view:**
```
Template Name: [Ransomware Response              ]
Slug:          [ransomware                       ]
Description:   [Template for ransomware incidents]

PHASES AND TASKS:
─ Phase 1 — Initial Response               [+ Add Task] [+ Add Phase]
  ≡  Isolate affected hosts from network     [CRITICAL] [Edit] [✕]
  ≡  Identify ransomware family and IoCs     [HIGH]     [Edit] [✕]
  ≡  Notify leadership and legal             [HIGH]     [Edit] [✕]

─ Phase 2 — Investigation                  [+ Add Task]
  ≡  Identify patient zero                   [CRITICAL] [Edit] [✕]
  ≡  Determine encryption scope              [CRITICAL] [Edit] [✕]

[+ Add Phase]

[Save Template]   [Preview Task Panel]
```

Tasks are reorderable via drag-and-drop (`@dnd-kit`). Phases can be renamed and reordered.

---

## 9. Admin Panel

At `/admin` — accessible to Admin role only.

### 9.1 Navigation

- **Team** — invite, list, role change, deactivate users
- **Organisation Settings** — name, license key, registration policy, branding
- **Storage** — storage backend configuration (this phase)
- **Incident Templates** — custom template builder
- **Audit Log** — premium gated

### 9.2 Team Management

```
TEAM MANAGEMENT                               [+ Invite User]

Name              Email                  Role              Last Seen   Status
John Doe          john.doe@co.com        Admin             2 min ago   Active  [Edit]
Jane Smith        jane.smith@co.com      Senior Analyst    1h ago      Active  [Edit]
Bob Wilson        bob.wilson@co.com      Analyst           3d ago      Active  [Edit]
Alice Chen        alice.chen@co.com      Viewer            Never       Invited [Resend] [Revoke]
```

### 9.3 Organisation Settings

```
Organisation Name:  [Acme Security Team              ]
Slug:               [acme-security                   ]
Plan:               Premium (expires 2027-01-01)
License Key:        [irp_lic_xxxxxxxxxxxxxxxxxxxx     ] [Verify]

Registration Policy:
  ○  Open (anyone with the link can register)
  ● Invite only (requires admin invitation)
  ○  SSO only (SAML users auto-provisioned)

Custom Branding:                               [PREMIUM]
  Logo:    [Upload logo PNG/SVG    ]
  Primary color: [#f97316          ]
```

---

## 10. Email Notifications

```env
EMAIL_BACKEND=smtp          # console | smtp | resend | sendgrid
SMTP_HOST=smtp.company.com
SMTP_PORT=587
SMTP_USER=irp-noreply@company.com
SMTP_PASSWORD=...
EMAIL_FROM=IRDoc <irp-noreply@company.com>
```

| Event | Recipients | Template |
|---|---|---|
| Invitation | Invitee | "You've been invited to join IRDoc" |
| Incident assigned | Assigned analyst | "You've been assigned to INC-2026-0315" |
| Report ready | Requester | "Your {type} report is ready to download" |
| Severity escalated | Assigned + admin | "Incident escalated to SEV-1: {title}" |
| SharePoint sync failed | Admin | "SharePoint sync failed for INC-XXXX: {error}" |
| Weekly digest | Admins | "This week: N incidents opened, N closed" |

---

## 11. New API Endpoints (Phase 5)

### Users & Team

| Method | Path | Description |
|---|---|---|
| GET    | `/users` | List org users (admin only) |
| POST   | `/users/invite` | Send invitation |
| GET    | `/users/invite/{token}` | Validate invite token |
| POST   | `/users/invite/{token}/accept` | Accept + create account |
| PUT    | `/users/{id}/role` | Change role (admin only) |
| PUT    | `/users/{id}/deactivate` | Deactivate (admin only) |

### SSO

| Method | Path | Description |
|---|---|---|
| GET    | `/auth/saml/metadata` | SP metadata XML |
| POST   | `/auth/saml/acs` | Assertion Consumer Service |
| GET    | `/auth/saml/config` | Get SSO configuration (admin) |
| PUT    | `/auth/saml/config` | Update SSO configuration |

### Audit Log

| Method | Path | Description |
|---|---|---|
| GET    | `/audit-log` | Paginated, filterable (admin, premium) |
| GET    | `/audit-log/export` | CSV export |

### Storage

| Method | Path | Description |
|---|---|---|
| GET    | `/admin/storage` | Current config (redacted) + stats |
| PUT    | `/admin/storage` | Update backend config |
| POST   | `/admin/storage/test` | Test connection |
| POST   | `/admin/storage/switch` | Activate new backend |

---

## 12. Deliverables Checklist

### Architect
- [ ] RBAC permission matrix reviewed — no gaps
- [ ] RLS policies tested with cross-org query attempt
- [ ] SAML flow threat-modeled (replay attacks, signature validation)
- [ ] Storage migration note reviewed — confirm existing files remain accessible after backend switch

### Developer (Backend)
- [ ] RBAC dependencies implemented on all relevant routes
- [ ] User invite system (create, email, validate, accept)
- [ ] Email service abstraction + SMTP adapter
- [ ] Invite email Jinja2 template
- [ ] Audit log service (write to all service-layer mutations)
- [ ] Audit log read + export endpoints
- [ ] SAML 2.0 (`python3-saml`) — SSO endpoints
- [ ] SSO config CRUD
- [ ] MSSP org isolation (RLS policies on all tables)
- [ ] S3StorageBackend implementation
- [ ] AzureBlobStorageBackend implementation
- [ ] GCSStorageBackend implementation
- [ ] Storage config CRUD + test + switch endpoints
- [ ] Storage backend factory (reads from `storage_configs` at startup)
- [ ] Custom incident template builder CRUD
- [ ] Admin user management endpoints
- [ ] Org settings endpoints

### Developer (Frontend)
- [ ] Admin panel layout (sidebar nav: Team, Org Settings, Storage, Templates, Audit Log)
- [ ] Team management (invite modal, role change, deactivate)
- [ ] Invite acceptance page (`/invite/{token}`)
- [ ] SSO configuration form
- [ ] Login page SSO button (conditional on SSO config)
- [ ] Audit log page (table, filters, CSV export — premium gated)
- [ ] Storage backend configuration UI (all 4 backends, test connection, switch)
- [ ] Custom incident template builder (phases + tasks drag/drop)
- [ ] Org settings page (name, license, registration policy, branding)
- [ ] Permission-aware UI rendering (hide/disable based on role)
- [ ] PremiumGate on SSO config, audit log, cloud storage backends, MSSP

### QA / Security
- [ ] Analyst cannot edit/delete another analyst's entry — returns 403
- [ ] Viewer cannot POST to any write endpoint — all return 403
- [ ] RLS test: directly query `SELECT * FROM incidents` from a connection authenticated as Org A — confirm Org B's incidents are absent
- [ ] SAML tested with Azure AD test tenant
- [ ] Invite token expires at 48h — reuse returns 410
- [ ] Invite token cannot be reused after acceptance
- [ ] S3 upload + presigned URL download works end-to-end
- [ ] Azure Blob upload + SAS URL works
- [ ] Switching storage backend: new uploads use new backend, old file URLs still work
- [ ] SHA-256 in DB matches `sha256sum` of the actual stored file (both backends)
- [ ] Audit log captures: incident create, timeline add, containment action, storage switch
- [ ] Last admin cannot be downgraded to analyst

---

*Next: Phase 6 — Hardening, Performance, Open-Source Launch & Docker Hub*
