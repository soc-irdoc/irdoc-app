# IRP Phase 1 — Foundation: Auth, Database & Core Backend

> **Status:** Planning  
> **Depends on:** Phase 0 complete and agreed  
> **Estimated effort:** 3–4 weeks (1–2 developers)  
> **Goal:** A running, authenticated, tested backend with a solid database schema. No frontend yet — just a working API you can test via `/api/docs`. This includes the storage backend abstraction, API key auth, and inbound webhook endpoint — all foundational pieces that every later phase depends on.

---

## 1. Objectives

By the end of Phase 1:
- Full database schema live and migratable via Alembic
- JWT auth (register, login, refresh, logout) working
- API key auth working (create, scope, use, revoke)
- Core CRUD for incidents, timeline, IOCs, evidence, tasks
- Inbound webhook endpoint (`POST /api/v1/external/incidents`) functional
- StorageBackend abstraction in place with local backend working
- Evidence upload with SHA-256 hashing working end-to-end
- Celery worker infrastructure running
- System incident templates seeded (phishing, credential compromise, malware, suspicious login)
- 80%+ test coverage on service-layer logic
- Everything runs with `docker compose up`

---

## 2. Database Schema

### 2.1 Full Schema (implemented as Alembic migrations)

```sql
-- Organizations (foundation for multi-tenancy, even if not activated in Core)
CREATE TABLE organizations (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT NOT NULL,
    slug         TEXT UNIQUE NOT NULL,
    plan         TEXT DEFAULT 'core',         -- core | pro | enterprise
    license_key  TEXT,
    settings     JSONB DEFAULT '{}',
    created_at   TIMESTAMPTZ DEFAULT now()
);

-- Users
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID REFERENCES organizations(id) ON DELETE CASCADE,
    email           TEXT UNIQUE NOT NULL,
    full_name       TEXT NOT NULL,
    role            TEXT DEFAULT 'analyst',   -- admin | senior_analyst | analyst | viewer
    password_hash   TEXT NOT NULL,            -- argon2id
    avatar_initials TEXT,
    timezone        TEXT DEFAULT 'UTC',
    theme           TEXT DEFAULT 'dark',
    is_active       BOOLEAN DEFAULT true,
    last_seen       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- API Keys (service-to-service auth — used by SDP, ManageEngine, Jira, etc.)
CREATE TABLE api_keys (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID REFERENCES organizations(id) ON DELETE CASCADE,
    created_by   UUID REFERENCES users(id),
    name         TEXT NOT NULL,               -- "ServiceDesk Plus Integration"
    key_prefix   TEXT NOT NULL,               -- "irp_key_" — shown in UI for identification
    key_hash     TEXT NOT NULL,               -- argon2id hash of full key — never stored plain
    scopes       TEXT[] DEFAULT '{}',         -- ["incidents:create", "incidents:read"]
    last_used_at TIMESTAMPTZ,
    expires_at   TIMESTAMPTZ,                 -- null = never expires
    is_active    BOOLEAN DEFAULT true,
    created_at   TIMESTAMPTZ DEFAULT now()
);

-- Incident Templates (define task checklists per incident type)
CREATE TABLE incident_templates (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID REFERENCES organizations(id),  -- null = system template
    name        TEXT NOT NULL,
    slug        TEXT NOT NULL,
    description TEXT,
    is_system   BOOLEAN DEFAULT false,
    tasks_json  JSONB NOT NULL DEFAULT '[]',
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- Incidents
CREATE TABLE incidents (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id           UUID REFERENCES organizations(id) ON DELETE CASCADE,
    incident_ref     TEXT UNIQUE NOT NULL,    -- INC-2026-0315
    title            TEXT NOT NULL,
    severity         TEXT DEFAULT 'sev1',     -- sev1 | sev2 | sev3 | sev4
    status           TEXT DEFAULT 'open',     -- open | contained | closed | monitoring
    template_id      UUID REFERENCES incident_templates(id),
    assigned_to      UUID REFERENCES users(id),
    created_by       UUID REFERENCES users(id),
    opened_at        TIMESTAMPTZ DEFAULT now(),
    contained_at     TIMESTAMPTZ,
    closed_at        TIMESTAMPTZ,
    executive_summary TEXT,
    attack_vector    TEXT[],
    affected_users   INT DEFAULT 0,
    metadata         JSONB DEFAULT '{}',
    created_at       TIMESTAMPTZ DEFAULT now(),
    updated_at       TIMESTAMPTZ DEFAULT now()
);

-- External References (links to SDP tickets, Jira issues, ManageEngine refs, etc.)
-- One incident can have refs from multiple external systems
CREATE TABLE incident_external_refs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id     UUID REFERENCES incidents(id) ON DELETE CASCADE,
    external_source TEXT NOT NULL,            -- "servicedesk_plus" | "jira" | "manage_engine" | "servicenow"
    external_ref    TEXT NOT NULL,            -- "SDP-2026-4421"
    external_url    TEXT,                     -- deep link back to original ticket
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(incident_id, external_source)      -- one ref per source per incident
);

-- Timeline Entries
CREATE TABLE timeline_entries (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id  UUID REFERENCES incidents(id) ON DELETE CASCADE,
    author_id    UUID REFERENCES users(id),
    entry_type   TEXT NOT NULL,              -- detection | analysis | containment | evidence | comms | note
    occurred_at  TIMESTAMPTZ NOT NULL,       -- analyst-set event time
    description  TEXT NOT NULL,
    source       TEXT DEFAULT 'manual',      -- manual | sentinel | crowdstrike | api | etc.
    is_pinned    BOOLEAN DEFAULT false,
    metadata     JSONB DEFAULT '{}',
    created_at   TIMESTAMPTZ DEFAULT now(),
    updated_at   TIMESTAMPTZ DEFAULT now()
);

-- Attachments (linked to timeline entries)
CREATE TABLE attachments (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id            UUID REFERENCES organizations(id),
    incident_id       UUID REFERENCES incidents(id) ON DELETE CASCADE,
    timeline_entry_id UUID REFERENCES timeline_entries(id) ON DELETE CASCADE,
    uploaded_by       UUID REFERENCES users(id),
    original_name     TEXT NOT NULL,
    stored_path       TEXT NOT NULL,         -- UUID-based path in storage backend
    mime_type         TEXT,
    file_size         BIGINT,
    sha256            TEXT NOT NULL,         -- computed during upload stream, ALWAYS stored here
    storage_backend   TEXT DEFAULT 'local',  -- local | s3 | azure_blob | gcs
    is_screenshot     BOOLEAN DEFAULT false,
    created_at        TIMESTAMPTZ DEFAULT now()
);

-- IOCs (Indicators of Compromise)
CREATE TABLE iocs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID REFERENCES incidents(id) ON DELETE CASCADE,
    ioc_type    TEXT NOT NULL,              -- email | domain | ip | url | hash | file | username
    value       TEXT NOT NULL,
    description TEXT,
    confidence  INT DEFAULT 50,            -- 0–100, recalculated after enrichment
    status      TEXT DEFAULT 'active',     -- active | blocked | remediated | fp
    first_seen  TIMESTAMPTZ DEFAULT now(),
    added_by    UUID REFERENCES users(id),
    enrichment  JSONB DEFAULT '{}',        -- VT, AbuseIPDB, Shodan results
    tlp_level   TEXT DEFAULT 'red',        -- TLP:RED | AMBER | GREEN | WHITE
    tags        TEXT[] DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- IOC ↔ Timeline Entry links
CREATE TABLE ioc_timeline_links (
    ioc_id            UUID REFERENCES iocs(id) ON DELETE CASCADE,
    timeline_entry_id UUID REFERENCES timeline_entries(id) ON DELETE CASCADE,
    PRIMARY KEY (ioc_id, timeline_entry_id)
);

-- Tasks
CREATE TABLE tasks (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id   UUID REFERENCES incidents(id) ON DELETE CASCADE,
    template_id   UUID REFERENCES incident_templates(id),
    title         TEXT NOT NULL,
    description   TEXT,
    phase         TEXT,
    priority      TEXT DEFAULT 'medium',   -- critical | high | medium | low
    status        TEXT DEFAULT 'pending',  -- pending | in_progress | done | skipped
    assigned_to   UUID REFERENCES users(id),
    completed_at  TIMESTAMPTZ,
    completed_by  UUID REFERENCES users(id),
    sort_order    INT DEFAULT 0,
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- Report Templates (org-level, reusable, schema-driven)
-- Detailed in Phase 3. Schema seeded here so the table exists from Phase 1.
CREATE TABLE report_templates (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID REFERENCES organizations(id),  -- null = system template
    name         TEXT NOT NULL,
    destination  TEXT DEFAULT 'custom',    -- management | analyst | legal | custom
    description  TEXT,
    is_system    BOOLEAN DEFAULT false,
    is_default   BOOLEAN DEFAULT false,    -- used as default for new incidents
    schema_json  JSONB NOT NULL DEFAULT '[]',  -- ordered block definitions
    created_by   UUID REFERENCES users(id),
    created_at   TIMESTAMPTZ DEFAULT now(),
    updated_at   TIMESTAMPTZ DEFAULT now()
);

-- Generated Reports
CREATE TABLE reports (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id       UUID REFERENCES incidents(id) ON DELETE CASCADE,
    report_template_id UUID REFERENCES report_templates(id),
    report_type       TEXT NOT NULL,       -- technical | executive | legal | custom
    destination       TEXT,               -- management | analyst | legal | custom
    format            TEXT NOT NULL,       -- pdf | docx | markdown | html
    classification    TEXT DEFAULT 'confidential',
    generated_by      UUID REFERENCES users(id),
    storage_path      TEXT,
    is_ai_assisted    BOOLEAN DEFAULT false,
    status            TEXT DEFAULT 'pending', -- pending | generating | ready | failed
    error_message     TEXT,
    generated_at      TIMESTAMPTZ,
    created_at        TIMESTAMPTZ DEFAULT now()
);

-- Sync Policies (SharePoint auto-sync and future destinations)
CREATE TABLE sync_policies (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id        UUID REFERENCES incidents(id) ON DELETE CASCADE,
    destination        TEXT NOT NULL,      -- sharepoint | future destinations
    report_template_id UUID REFERENCES report_templates(id),
    is_active          BOOLEAN DEFAULT true,
    trigger_type       TEXT DEFAULT 'on_change', -- on_change | on_close | manual
    debounce_seconds   INT DEFAULT 60,
    destination_config JSONB NOT NULL DEFAULT '{}', -- encrypted storage of SP URL/library/etc.
    last_synced_at     TIMESTAMPTZ,
    last_sync_status   TEXT,              -- success | failed
    last_error         TEXT,
    created_by         UUID REFERENCES users(id),
    created_at         TIMESTAMPTZ DEFAULT now()
);

-- Storage Configuration (one active config per org)
CREATE TABLE storage_configs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID REFERENCES organizations(id) UNIQUE,
    backend     TEXT DEFAULT 'local',     -- local | s3 | azure_blob | gcs
    config      JSONB DEFAULT '{}',       -- Fernet-encrypted credentials
    is_active   BOOLEAN DEFAULT true,
    last_tested TIMESTAMPTZ,
    test_status TEXT,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- Audit Log
CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    org_id      UUID REFERENCES organizations(id),
    user_id     UUID REFERENCES users(id),
    api_key_id  UUID REFERENCES api_keys(id),  -- populated for API key actions
    action      TEXT NOT NULL,
    entity_type TEXT,
    entity_id   UUID,
    diff        JSONB,
    ip_address  INET,
    user_agent  TEXT,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_timeline_incident_time  ON timeline_entries (incident_id, occurred_at DESC);
CREATE INDEX idx_timeline_fts            ON timeline_entries USING gin(to_tsvector('english', description));
CREATE INDEX idx_ioc_incident            ON iocs (incident_id, ioc_type);
CREATE INDEX idx_ioc_value               ON iocs (value);
CREATE INDEX idx_tasks_incident          ON tasks (incident_id, status);
CREATE INDEX idx_attachments_entry       ON attachments (timeline_entry_id);
CREATE INDEX idx_incidents_ref           ON incidents (incident_ref);
CREATE INDEX idx_incidents_org_status    ON incidents (org_id, status, severity);
CREATE INDEX idx_external_refs_incident  ON incident_external_refs (incident_id);
CREATE INDEX idx_external_refs_source    ON incident_external_refs (external_source, external_ref);
CREATE INDEX idx_audit_org_time          ON audit_log (org_id, created_at DESC);
CREATE INDEX idx_api_keys_org            ON api_keys (org_id, is_active);
```

### 2.2 Migration Strategy
- All schema changes via Alembic (`alembic revision --autogenerate`)
- Migrations run automatically on container startup via `entrypoint.sh`
- Seed script provides: default organization, default admin user, 4 system incident templates, 3 system report templates

---

## 3. StorageBackend Abstraction

This must be built in Phase 1 even though only the local backend is used until Phase 5. Every file operation after this point goes through the abstraction — retrofitting it later would be expensive.

```python
# app/services/storage/base.py
from typing import Protocol, runtime_checkable

@runtime_checkable
class StorageBackend(Protocol):
    backend_name: str

    async def store(self, data: bytes, path: str) -> str:
        """Store bytes at path. Returns the final stored path."""
        ...

    async def retrieve(self, path: str) -> bytes:
        """Retrieve file bytes by path."""
        ...

    async def delete(self, path: str) -> None:
        """Delete file at path."""
        ...

    async def get_url(self, path: str, expires_in: int = 3600) -> str:
        """Return a URL to access the file. Local backend uses a signed token endpoint.
        Cloud backends return presigned URLs."""
        ...

    async def test_connection(self) -> bool:
        """Verify backend is reachable and credentials are valid."""
        ...


# app/services/storage/local.py
class LocalStorageBackend:
    backend_name = "local"

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

    async def store(self, data: bytes, path: str) -> str:
        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        return path

    async def get_url(self, path: str, expires_in: int = 3600) -> str:
        # Signs a token: GET /api/v1/files/{signed_token} serves the file
        token = sign_file_token(path, expires_in)
        return f"/api/v1/files/{token}"

    async def test_connection(self) -> bool:
        return self.base_path.exists() and os.access(self.base_path, os.W_OK)
```

The active backend is loaded at startup from the org's `storage_configs` row (or from `STORAGE_BACKEND` env var for single-org deployments). All attachment service methods call `storage_backend.store(...)` — never filesystem directly.

**SHA-256 integrity rule:** Hash is always computed during the upload stream using `hashlib.sha256()` with chunked reading — before the file is passed to the storage backend. The hash is stored in the `attachments.sha256` column unconditionally, regardless of backend. This guarantees forensic integrity even if files are later migrated between backends.

---

## 4. API Key Authentication

API keys are used by external systems (SDP, ManageEngine, Jira, custom scripts) to call the inbound webhook endpoint. They may also be used for CI/CD pipelines or automation scripts that read incident data.

```python
# app/core/security.py

# Key format: irp_key_{random_32_hex}
# The full key is shown exactly once at creation. Afterwards only the prefix is shown.
# The key_hash (argon2id) is stored in the DB.

async def create_api_key(org_id, name, scopes, created_by) -> tuple[APIKey, str]:
    raw_key = f"irp_key_{secrets.token_hex(32)}"
    key_hash = argon2.hash(raw_key)
    api_key = APIKey(
        org_id=org_id,
        name=name,
        key_prefix=raw_key[:16],  # "irp_key_a3f92b..." shown in UI for identification
        key_hash=key_hash,
        scopes=scopes,
        created_by=created_by
    )
    db.add(api_key)
    return api_key, raw_key  # raw_key returned only here, never again

async def verify_api_key(raw_key: str) -> APIKey | None:
    # Extract prefix, find candidate rows, verify hash
    prefix = raw_key[:16]
    candidates = db.query(APIKey).filter_by(key_prefix=prefix, is_active=True).all()
    for candidate in candidates:
        if argon2.verify(raw_key, candidate.key_hash):
            candidate.last_used_at = datetime.utcnow()
            return candidate
    return None
```

### API Key Scopes

| Scope | Description |
|---|---|
| `incidents:create` | Create incidents via external webhook |
| `incidents:read` | Read incident data (for external dashboards) |
| `incidents:write` | Update incident metadata |
| `timeline:read` | Read timeline entries |
| `iocs:read` | Read IOCs |
| `reports:read` | Download generated reports |

The inbound webhook endpoint (`POST /api/v1/external/incidents`) requires the `incidents:create` scope.

---

## 5. Inbound Webhook API

This endpoint is the foundation of the service desk integration. It is intentionally simple — any tool that can POST JSON can use it.

```python
# app/api/v1/external.py

@router.post("/external/incidents", status_code=201)
async def create_incident_from_external(
    payload: ExternalIncidentCreate,
    api_key: APIKey = Depends(require_api_key_scope("incidents:create"))
):
    """
    Creates a new incident from an external service desk tool.
    Instantiates the task template, stores the external reference,
    and optionally fires a Slack notification.
    """
    incident = await incident_service.create(
        org_id=api_key.org_id,
        title=payload.title,
        severity=payload.severity,
        template_slug=payload.template,
        created_via="api_key",
        created_by_key_id=api_key.id
    )

    if payload.external_ref:
        await db.add(IncidentExternalRef(
            incident_id=incident.id,
            external_source=payload.external_source,
            external_ref=payload.external_ref,
            external_url=payload.external_url
        ))

    return {
        "incident_id": str(incident.id),
        "incident_ref": incident.incident_ref,
        "external_ref": payload.external_ref,
        "workspace_url": f"{settings.BASE_URL}/incidents/{incident.id}"
    }
```

```python
# Pydantic schema for the inbound payload
class ExternalIncidentCreate(BaseModel):
    title: str
    severity: Literal["sev1", "sev2", "sev3", "sev4"] = "sev2"
    template: str = "blank"              # matches incident_template.slug
    external_ref: str | None = None      # "SDP-2026-4421"
    external_source: str | None = None   # "servicedesk_plus"
    external_url: str | None = None      # https://sdp.company.com/requests/4421
    description: str | None = None       # pre-populate first timeline entry
    reported_by: str | None = None       # email of original reporter
```

If `description` is provided, a first timeline entry of type `note` is automatically created with the content and source set to `external_source`. This gives analysts immediate context the moment they open the case.

---

## 6. Backend API Endpoints (Full List for Phase 1)

### Auth (`/api/v1/auth`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | None | Create account (if open registration enabled) |
| POST | `/auth/login` | None | Returns JWT; sets refresh cookie |
| POST | `/auth/refresh` | Cookie | Rotate access token |
| POST | `/auth/logout` | JWT | Invalidate refresh token |
| GET  | `/auth/me` | JWT | Current user profile |
| PUT  | `/auth/me` | JWT | Update profile |
| POST | `/auth/change-password` | JWT | Change own password |
| GET  | `/setup` | None | First-run setup check (disables after first user) |
| POST | `/setup` | None | Create first admin account |

### API Keys (`/api/v1/api-keys`)

| Method | Path | Description |
|---|---|---|
| GET    | `/api-keys` | List org API keys (name, prefix, scopes, last_used — never hash) |
| POST   | `/api-keys` | Create key — returns full key ONCE |
| DELETE | `/api-keys/{id}` | Revoke key |

### Incidents (`/api/v1/incidents`)

| Method | Path | Description |
|---|---|---|
| GET    | `/incidents` | List (paginated, filter by status/severity/search) |
| POST   | `/incidents` | Create (with optional template_id) |
| GET    | `/incidents/{id}` | Full incident detail including external_refs |
| PUT    | `/incidents/{id}` | Update |
| DELETE | `/incidents/{id}` | Soft-delete |
| GET    | `/incidents/{id}/stats` | Entry count, IOC count, task progress, duration |
| GET    | `/incidents/{id}/external-refs` | List external references |
| POST   | `/incidents/{id}/external-refs` | Manually add external ref |

### Timeline (`/api/v1/incidents/{id}/timeline`)

| Method | Path | Description |
|---|---|---|
| GET    | `/timeline` | List (filterable by type, paginated) |
| POST   | `/timeline` | Add entry |
| PUT    | `/timeline/{entry_id}` | Edit entry |
| DELETE | `/timeline/{entry_id}` | Delete entry |
| POST   | `/timeline/{entry_id}/pin` | Pin/unpin |
| GET    | `/timeline/export/csv` | CSV export |

### Attachments (`/api/v1/incidents/{id}/attachments`)

| Method | Path | Description |
|---|---|---|
| POST   | `/attachments` | Upload file (multipart/form-data) — returns sha256, stored_path |
| GET    | `/attachments/{id}/url` | Get time-limited access URL |
| DELETE | `/attachments/{id}` | Delete |
| GET    | `/files/{token}` | Serve file (local backend signed token endpoint) |

### IOCs (`/api/v1/incidents/{id}/iocs`)

| Method | Path | Description |
|---|---|---|
| GET    | `/iocs` | List IOCs |
| POST   | `/iocs` | Add single IOC |
| POST   | `/iocs/bulk` | Bulk import (paste text, auto-type detection) |
| PUT    | `/iocs/{id}` | Update status, confidence, description |
| DELETE | `/iocs/{id}` | Delete |

### Tasks (`/api/v1/incidents/{id}/tasks`)

| Method | Path | Description |
|---|---|---|
| GET    | `/tasks` | List all tasks |
| PUT    | `/tasks/{id}` | Update (status, assigned_to) |
| POST   | `/tasks` | Add ad-hoc task |
| DELETE | `/tasks/{id}` | Remove |

### Templates (`/api/v1/templates`)

| Method | Path | Description |
|---|---|---|
| GET    | `/templates` | List system + org templates |
| POST   | `/templates` | Create custom template |
| PUT    | `/templates/{id}` | Edit (org templates only) |
| DELETE | `/templates/{id}` | Delete (org templates only) |

### External Inbound (`/api/v1/external`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/external/incidents` | ApiKey | Create incident from service desk |

### Features (`/api/v1/features`)

| Method | Path | Description |
|---|---|---|
| GET | `/features` | Feature flag map for current org |

### Health (`/api/health`)

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Returns DB + Redis + storage connectivity status |

---

## 7. Service Layer

All business logic lives in `services/` — routes are thin.

```
services/
├── incident_service.py      # create, update, soft-delete, stats, ref number generation
├── timeline_service.py      # CRUD + auto-link IOC mentions in description text
├── ioc_service.py           # CRUD + auto-type detection regex
├── attachment_service.py    # stream upload, compute sha256, delegate to StorageBackend
├── task_service.py          # instantiate from template, progress calc
├── template_service.py      # CRUD + seed system templates
├── auth_service.py          # JWT, password hashing, refresh tokens
├── api_key_service.py       # key creation, verification, scope check
├── user_service.py          # profile, role management
├── external_service.py      # inbound webhook logic, source normalization
├── storage_service.py       # backend resolution, config management
└── report_service.py        # stub in Phase 1, implemented in Phase 3
```

### Key service: `incident_service.generate_ref()`

```python
def generate_ref(org_id: str) -> str:
    """
    Generates INC-YYYY-NNNN where NNNN is zero-padded sequential per org per year.
    Thread-safe via DB sequence: SELECT nextval('incident_seq_{org_id}_{year}')
    """
```

### Key service: `ioc_service.auto_detect(text)`

```python
PATTERNS = {
    "ip":     re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
    "domain": re.compile(r'\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b'),
    "email":  re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'),
    "md5":    re.compile(r'\b[a-fA-F0-9]{32}\b'),
    "sha1":   re.compile(r'\b[a-fA-F0-9]{40}\b'),
    "sha256": re.compile(r'\b[a-fA-F0-9]{64}\b'),
    "url":    re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+'),
}

def auto_detect(text: str) -> list[dict]:
    """Scan free text and return suggested IOCs with detected type."""
```

---

## 8. Background Workers (Celery — Phase 1 Stubs)

The worker infrastructure must exist from Phase 1, even if most tasks are stubs.

```python
# workers/tasks.py

@celery_app.task
def verify_file_hash(attachment_id: str):
    """Re-verify SHA-256 after storage. Logs mismatch as a security event."""

@celery_app.task
def auto_detect_iocs_from_entry(entry_id: str):
    """After a timeline entry is saved, scan description for IOC patterns
    and create suggested IOCs linked to the entry. Does not auto-add —
    surfaces as suggestions in the UI for analyst to confirm."""

@celery_app.task
def send_notification(org_id: str, event: str, payload: dict):
    """Stub — wired up to Slack/Teams in Phase 4."""

@celery_app.task
def sync_to_sharepoint(incident_id: str, policy_id: str):
    """Stub — implemented in Phase 4. Debounce lock managed in Redis."""
```

### Debounce Lock Pattern (for SharePoint, used from Phase 4 onwards)

```python
# app/core/debounce.py

def trigger_debounced_sync(incident_id: str, policy_id: str, debounce_seconds: int = 60):
    """
    Sets a Redis key with TTL. If key already exists, resets TTL (debounce).
    A separate Celery beat task checks for expired locks every 10 seconds
    and fires the actual sync task.
    """
    redis.set(
        f"sync_pending:{incident_id}:{policy_id}",
        value=policy_id,
        ex=debounce_seconds
    )
```

This debounce infrastructure is wired in Phase 1 so that any write to an incident can call `trigger_debounced_sync()` without needing to know whether a sync policy exists — the sync worker checks for active policies.

---

## 9. Seed Data

On first startup, the seed script creates:

1. **Default organization** (`slug: default`)
2. **Admin user** (`admin@localhost` — password forced-reset on first login)
3. **4 system incident templates** — phishing, credential compromise, malware infection, suspicious login (full task lists as defined in original Phase 1 document)
4. **3 system report templates:**
   - Management Brief (destination: management, schema: cover + executive summary + stat row + active IOCs + containment actions + recommendations)
   - Technical Report (destination: analyst, schema: full timeline + all IOCs + evidence register + all tasks + analyst notes)
   - Legal/Compliance (destination: legal, schema: incident overview + affected data + detection timeline + response timeline + regulatory fields)

---

## 10. Environment Variables (`.env.example`)

```env
# Database
DB_PASSWORD=changeme_strong_password
DATABASE_URL=postgresql+asyncpg://irp:changeme@db/irp

# Redis
REDIS_PASSWORD=changeme_redis_password
REDIS_URL=redis://:changeme@redis:6379/0

# Security
SECRET_KEY=generate_with_openssl_rand_hex_32
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# Storage
STORAGE_BACKEND=local
STORAGE_PATH=/app/storage
# For S3 (premium): configure in admin UI, not here

# App
APP_NAME=IRDoc
BASE_URL=http://localhost:3000
ALLOW_REGISTRATION=true        # set false in production to require invites

# Feature License (leave empty for core)
LICENSE_KEY=

# Inbound Webhook
WEBHOOK_RATE_LIMIT=20          # requests per minute per API key
WEBHOOK_MAX_PAYLOAD_BYTES=65536

# Email (for invites — Phase 5)
EMAIL_BACKEND=console          # console | smtp | resend
```

---

## 11. Docker Compose

```yaml
version: '3.9'
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: irp
      POSTGRES_USER: irp
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "irp"]
      interval: 10s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}

  backend:
    build: ./backend
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      SECRET_KEY: ${SECRET_KEY}
      STORAGE_BACKEND: ${STORAGE_BACKEND:-local}
      STORAGE_PATH: /app/storage
      BASE_URL: ${BASE_URL}
    volumes:
      - ./storage:/app/storage
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "8000:8000"

  worker:
    build: ./backend
    command: celery -A app.workers.celery_app worker --loglevel=info
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      SECRET_KEY: ${SECRET_KEY}
      STORAGE_PATH: /app/storage
    volumes:
      - ./storage:/app/storage
    depends_on: [db, redis]

volumes:
  postgres_data:
```

---

## 12. Testing Strategy

| Type | Tool | Target |
|---|---|---|
| Unit (service logic) | pytest | 80%+ |
| API integration | pytest + httpx | All endpoints |
| Storage backend | pytest | Local read/write/delete/hash |
| Auth flows | pytest | JWT + API key paths |
| Inbound webhook | pytest | Valid + invalid payloads, scope enforcement |

```
tests/
├── unit/
│   ├── test_ioc_service.py          # auto_detect patterns
│   ├── test_attachment_service.py   # sha256 integrity
│   ├── test_task_service.py         # template instantiation
│   ├── test_storage_local.py        # LocalStorageBackend
│   └── test_api_key_service.py      # key creation, verification, scope
├── integration/
│   ├── test_auth.py
│   ├── test_incidents.py
│   ├── test_timeline.py
│   ├── test_iocs.py
│   ├── test_external_webhook.py     # inbound API key endpoint
│   └── test_attachments.py
└── conftest.py
```

---

## 13. Deliverables Checklist

### Architect
- [ ] Schema reviewed and approved — especially `incident_external_refs` and `sync_policies`
- [ ] StorageBackend protocol interface finalized
- [ ] API key scope list finalized
- [ ] Report template schema format validated (JSONB block array)

### Developer (Backend)
- [ ] PostgreSQL schema + all Alembic migrations
- [ ] Seed script (org, admin, 4 incident templates, 3 report templates)
- [ ] FastAPI app with all routers registered
- [ ] Auth endpoints (register, login, refresh, logout, me, setup)
- [ ] API key endpoints (create, list, revoke)
- [ ] Incident CRUD + `incident_ref` generation + external refs
- [ ] Timeline CRUD + CSV export
- [ ] Attachment upload + SHA-256 + StorageBackend delegation + signed URL serving
- [ ] IOC CRUD + auto-detect regex
- [ ] Task CRUD + template instantiation
- [ ] Template CRUD
- [ ] Feature flags endpoint
- [ ] Inbound webhook endpoint (`POST /external/incidents`)
- [ ] Celery app + 4 initial tasks (stubs where noted)
- [ ] Debounce lock utility (Redis-based)
- [ ] Health endpoint

### DevOps
- [ ] `docker-compose.yml` running clean
- [ ] `entrypoint.sh` running migrations + seed on first start
- [ ] `.env.example` complete

### QA
- [ ] All unit + integration tests passing
- [ ] API docs accessible at `/api/docs`
- [ ] Inbound webhook tested with curl (valid key, missing scope, invalid payload)
- [ ] SHA-256 verified: upload a file, confirm hash in DB matches local sha256sum

### Product Owner
- [ ] Walk through all endpoints in Swagger UI
- [ ] Create an incident via the inbound webhook endpoint manually
- [ ] Confirm external_ref is stored and returned correctly

---

*Next: Phase 2 — Frontend: React Application*
