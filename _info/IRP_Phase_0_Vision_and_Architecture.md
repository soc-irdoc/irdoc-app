# IRP Phase 0 — Vision, Architecture & Foundational Decisions

> **Status:** Planning  
> **Audience:** Founders, Architect, Lead Developer, Product Owner  
> **Purpose:** Establish the non-negotiable decisions that every subsequent phase will build on. Nothing gets coded until this document is agreed upon.

---

## 1. Product Vision

**IRDoc** is a self-hostable, open-core Incident Response Documentation Platform built for SOC analysts, IR engineers, and MSSPs.

The core promise:
> *"Document incidents the way you actually investigate them — fast, structured, and reportable in one click."*

### Open-Core Licensing Model

| Layer | License | Description |
|---|---|---|
| **Core** | AGPL-3.0 | Timeline, IOCs, Evidence, Tasks, Basic Report Export (Markdown/HTML), Inbound Webhook API, Local File Storage, REST API |
| **Premium** | Commercial key | Visual Report Template Builder, multi-destination reports (PDF/DOCX), AI summaries, SharePoint auto-sync, cloud storage backends (S3/Azure/GCS), advanced integrations, multi-tenancy, SSO/SAML, audit logs, custom branding |

This model allows:
- Free self-hosting for individuals and small teams (drives adoption)
- Revenue from organizations that need enterprise features
- Community contributions to the core
- Docker-first deployment (portable, maintainable)

---

## 2. What We Are Building (and What We Are Not)

### We ARE building:
- A focused **incident workspace** — not a SIEM, not a ticketing system
- A **documentation-first** tool that integrates with existing security tools
- A **timeline-centric** interface (the prototype already proves this works)
- A **report generator** with a visual, field-based template builder — not fixed layouts. Analysts compose report templates from available case fields and save them per destination (management, analysts, legal, etc.)
- A **live management reporting layer** via SharePoint auto-sync — every time a case is updated, the management-facing document on SharePoint regenerates automatically. Management is always current without needing access to the platform
- An **inbound API** so service desk tools (SDP, ManageEngine, Jira, ServiceNow) can create IRDoc cases carrying the original ticket reference, so one number is used everywhere
- A **pluggable storage backend** — local Docker volume, S3-compatible, Azure Blob, GCS — configurable per deployment
- A **portable, self-hosted** product (Docker, no vendor lock-in)

### We are NOT building:
- A SIEM replacement
- A full EDR/MDR platform
- A case management system with billing/SLA tracking (that is ServiceNow's job)
- A real-time alerting platform
- A bidirectional ticket sync engine — IRDoc receives from service desks in v1; writing back is a future consideration

---

## 3. Confirmed Tech Stack & Rationale

### Why this stack was chosen

The goal is maximum portability, developer familiarity in the security community, and the ability to run on any Linux box or cloud VM.

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend                            │
│  React 18 + TypeScript                                  │
│  Vite (build tool — fast dev, small bundles)            │
│  Tailwind CSS (utility-first, keeps the design system   │
│   consistent with the prototype's CSS variable approach)│
│  Zustand (lightweight global state)                     │
│  React Query / TanStack Query (server state, caching)   │
│  React Router v6 (SPA routing)                          │
│  @dnd-kit/core (drag-and-drop: report builder, tasks)   │
└─────────────────────────────────────────────────────────┘
         ↕ REST API + WebSocket (Socket.io)
┌─────────────────────────────────────────────────────────┐
│                     Backend                             │
│  Python 3.12 + FastAPI                                  │
│  SQLAlchemy 2 ORM + Alembic (migrations)                │
│  Pydantic v2 (validation, serialization)                │
│  Celery + Redis (background tasks: report generation,   │
│   AI calls, IOC enrichment, SharePoint debounced sync)  │
│  Jinja2 (report rendering engine)                       │
│  WeasyPrint (HTML → PDF, server-side, no Chrome needed) │
│  python-docx (DOCX export — premium)                    │
│  Pluggable StorageBackend protocol                      │
└─────────────────────────────────────────────────────────┘
         ↕ SQLAlchemy / psycopg2
┌─────────────────────────────────────────────────────────┐
│                     Database                            │
│  PostgreSQL 16 (primary — relational, JSONB for         │
│   flexible metadata, report template schemas,           │
│   enrichment data, full-text search built-in)           │
│  Redis 7 (task queue, session cache, pub/sub for        │
│   real-time collaboration, debounce locks)              │
└─────────────────────────────────────────────────────────┘
         ↕ Docker Compose / Kubernetes
┌─────────────────────────────────────────────────────────┐
│                  Infrastructure                         │
│  Docker + Docker Compose (primary deployment)           │
│  Nginx (reverse proxy, static file serving)             │
│  Optional: Kubernetes Helm chart (enterprise)           │
└─────────────────────────────────────────────────────────┘
```

### Stack Decision Notes

**FastAPI over Django/Flask:**
- Auto-generates OpenAPI docs — critical for the integration ecosystem and the inbound webhook API that service desks will call
- Native async support for WebSocket real-time features and async storage operations
- Pydantic-native — strict data validation of IOCs, evidence metadata, inbound webhook payloads, and report template schemas
- Less boilerplate for clean REST APIs

**PostgreSQL over SQLite/MySQL:**
- JSONB for flexible metadata: timeline entries, report template schemas, IOC enrichment data, storage configs, sync policies
- Full-text search (`tsvector`) for natural language incident search — no Elasticsearch needed in MVP
- Row-level security for multi-tenancy (Phase 5)
- Battle-tested for concurrent analyst writes

**React + TypeScript over Vue/Svelte:**
- Largest ecosystem for security/enterprise tooling
- The prototype's component model maps cleanly to React components
- TypeScript gives compile-time safety on complex data models (incidents, IOCs, report template schemas)
- `@dnd-kit` for the report builder and task reordering

**Redis:**
- Celery broker for async jobs (report generation, file hashing, AI calls)
- Pub/Sub for live collaboration (analyst B sees analyst A's new timeline entry in real time)
- Debounce locks for SharePoint auto-sync (prevents repeated uploads on rapid edits)
- Session storage

**Why NOT a monorepo with Next.js:**
- SSR is unnecessary — this is a full app, not a public website
- Separate frontend/backend repos are cleaner for open-source contribution and independent scaling

---

## 4. Repository Structure

```
irp-platform/
├── backend/                    # Python/FastAPI
│   ├── app/
│   │   ├── api/               # Route handlers (v1/)
│   │   │   └── v1/
│   │   │       ├── incidents.py
│   │   │       ├── timeline.py
│   │   │       ├── iocs.py
│   │   │       ├── evidence.py
│   │   │       ├── tasks.py
│   │   │       ├── reports.py
│   │   │       ├── report_templates.py  # Visual template builder API
│   │   │       ├── users.py
│   │   │       ├── integrations.py
│   │   │       ├── storage.py           # Storage backend management API
│   │   │       └── external.py          # Inbound webhook API (SDP, ManageEngine, etc.)
│   │   ├── core/              # Config, security, feature flags
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic schemas (request/response)
│   │   ├── services/          # Business logic (separated from routes)
│   │   │   ├── storage/       # StorageBackend adapters
│   │   │   │   ├── base.py    # Protocol definition
│   │   │   │   ├── local.py
│   │   │   │   ├── s3.py      # Covers AWS S3, MinIO, R2, Wasabi
│   │   │   │   ├── azure_blob.py
│   │   │   │   └── gcs.py
│   │   │   └── report_renderer/  # Schema-driven Jinja2 rendering engine
│   │   │       ├── engine.py
│   │   │       └── blocks/    # One .py per block type (header, timeline, ioc_table, etc.)
│   │   ├── workers/           # Celery tasks
│   │   └── plugins/           # Integration adapters (pluggable registry)
│   ├── templates/             # Jinja2 report templates (block partials + base layouts)
│   │   └── reports/
│   │       ├── base.html
│   │       ├── blocks/        # Partial template per block type
│   │       └── styles/
│   ├── alembic/               # DB migrations
│   ├── tests/
│   └── Dockerfile
│
├── frontend/                   # React/TypeScript
│   ├── src/
│   │   ├── components/
│   │   │   ├── timeline/
│   │   │   ├── ioc/
│   │   │   ├── evidence/
│   │   │   ├── reports/
│   │   │   │   ├── builder/   # Visual report template builder (drag/drop)
│   │   │   │   └── viewer/    # Rendered report preview
│   │   │   └── common/
│   │   ├── pages/
│   │   ├── stores/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── types/
│   │   └── styles/
│   ├── public/
│   └── Dockerfile
│
├── docker/
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── nginx/nginx.conf
│
├── docs/
├── .github/workflows/
├── LICENSE                     # AGPL-3.0
├── LICENSE-COMMERCIAL.md
└── README.md
```

---

## 5. Core Data Model (High-Level)

This is the conceptual data model. Detailed schemas are in Phase 1.

```
Organization
  └── Users (many)
  └── APIKeys (many)                    ← service-to-service auth (SDP, ManageEngine, etc.)
  └── StorageConfig (1)                 ← active storage backend + encrypted credentials
  └── ReportTemplates (many)            ← org-level reusable templates per destination
  └── IncidentTemplates (many)          ← task checklists per incident type
  └── Incidents (many)
        └── ExternalRefs (many)         ← SDP ticket, Jira issue, ManageEngine ref, etc.
        └── TimelineEntries (many)
        │     └── Attachments (many)    ← stored via StorageBackend, hash in DB
        │     └── IOCLinks (many-to-many)
        └── IOCs (many)
        │     └── EnrichmentData (JSONB)
        └── Evidence (many)
        │     └── FileHash (sha256, always in DB, independent of storage location)
        └── Tasks (many, from template)
        └── Reports (many, generated)   ← uses a ReportTemplate schema at render time
        └── SyncPolicies (many)         ← SharePoint/external auto-sync rules with debounce
```

---

## 6. Feature Flag / Plugin Architecture

This is the mechanism that separates Core (free) from Premium (paid).

```python
# backend/app/core/features.py
FEATURES = {
    # Core — always available
    "timeline":                   True,
    "iocs":                       True,
    "evidence":                   True,
    "tasks":                      True,
    "basic_reports":              True,   # Markdown + HTML export only
    "rest_api":                   True,
    "inbound_webhook_api":        True,   # External case creation (SDP, ManageEngine, Jira)
    "storage_local":              True,   # Local Docker volume storage

    # Premium — require valid license key
    "report_template_builder":    check_license("reports"),  # Visual drag/drop builder
    "report_multi_destination":   check_license("reports"),  # Named destinations
    "report_pdf_export":          check_license("reports"),  # PDF via WeasyPrint
    "report_docx_export":         check_license("reports"),  # DOCX via python-docx
    "sharepoint_autosync":        check_license("integrations"),
    "storage_s3":                 check_license("storage"),
    "storage_azure_blob":         check_license("storage"),
    "storage_gcs":                check_license("storage"),
    "ai_summary":                 check_license("ai"),
    "ai_ioc_enrichment":          check_license("ai"),
    "multi_tenancy":              check_license("enterprise"),
    "sso_saml":                   check_license("enterprise"),
    "advanced_integrations":      check_license("integrations"),
    "audit_log":                  check_license("enterprise"),
    "custom_branding":            check_license("enterprise"),
    "mssp_mode":                  check_license("enterprise"),
}
```

The frontend checks feature flags on app load via `/api/v1/features`. Premium features are always visible in the UI but gated with a lock overlay — the user sees what they would get, which motivates upgrading. Never a hard 404.

---

## 7. Key Architectural Concepts

### 7.1 Report Template Architecture (Schema-Driven)

Reports are **not** fixed Jinja2 templates baked into the codebase. They are user-defined schemas stored in the database as JSONB, interpreted at render time by a schema-driven engine. This is the single most important architectural decision in the report system.

```
ReportTemplate (DB row — org-level, reusable)
  name:        "Management Brief"
  destination: "management"         ← management | analyst | legal | custom
  schema: [                         ← ordered array of block definitions
    { "type": "cover",        "fields": ["incident.title", "incident.ref", "incident.severity", "generated_at"] },
    { "type": "section",      "label": "Executive Summary",   "field": "incident.executive_summary" },
    { "type": "stat_row",     "fields": ["incident.severity", "incident.duration", "incident.affected_users", "incident.status"] },
    { "type": "section",      "label": "Attack Overview",     "field": "incident.attack_vector_tags" },
    { "type": "ioc_table",    "filter": "status=active",      "columns": ["type", "value", "status", "confidence"] },
    { "type": "timeline",     "filter": "type=containment",   "show_attachments": false },
    { "type": "task_list",    "filter": "phase=3",            "show_completed": true },
    { "type": "text_block",   "label": "Recommendations",     "field": "ai.recommendations" }
  ]
```

The rendering engine iterates the schema blocks, renders each to a Jinja2 partial (`templates/reports/blocks/{type}.html`), assembles them under a base layout, and passes the result to WeasyPrint (PDF) or python-docx (DOCX). Adding a new block type requires only a new Jinja2 partial and a renderer entry — no DB migrations, no frontend rebuild.

**Three default system templates ship with the app:**
- Management Brief — cover, executive summary, stat row, active IOCs summary, containment actions, recommendations
- Technical Report — full timeline, all IOCs with enrichment, evidence register, all tasks, analyst notes
- Legal / Compliance — incident overview, affected data description, detection and response timeline, regulatory fields

Organizations can clone and edit these, or build their own from scratch.

### 7.2 SharePoint Auto-Sync (Debounced, Always Current)

SharePoint sync is a **sync policy** attached to an incident — not a button. Every time the incident is modified (new timeline entry, task ticked, IOC added, summary edited), a Celery task is queued with a Redis debounce lock.

```
Incident modified
  → Check: does this incident have an active SyncPolicy for SharePoint?
  → Yes: set Redis key "sync_lock:{incident_id}" with 60-second TTL
  → If key already exists: reset TTL (debounce — another change came in)
  → After 60 seconds of no changes: Redis key expires → triggers sync task

Celery task: sync_to_sharepoint(incident_id, policy_id)
  → Render report using the policy's linked ReportTemplate
  → Upload to SharePoint via Microsoft Graph API
  → Update SyncPolicy.last_synced_at and last_sync_status
  → Emit WebSocket: "sync:complete" { policy_id, url }
```

Management always has a live link. The document on SharePoint updates itself. No analyst needs to manually generate or send anything.

### 7.3 Inbound Webhook API (External Case Creation)

A dedicated public API surface for service desk tools to push new cases into IRDoc. Authenticated via API keys (not JWT — this is service-to-service). The `external_ref` and `external_source` fields are stored and displayed throughout the UI alongside the IRDoc reference, so one number flows everywhere.

```http
POST /api/v1/external/incidents
Authorization: ApiKey irp_key_xxxxxxxxxxxx

{
  "title": "Suspected phishing - Finance team",
  "severity": "sev1",
  "template": "phishing",
  "external_ref": "SDP-2026-4421",
  "external_source": "servicedesk_plus",
  "external_url": "https://sdp.company.com/requests/4421",
  "description": "User reported suspicious email from unknown sender.",
  "reported_by": "jane.smith@company.com"
}

→ 201 Created
{
  "incident_id": "uuid...",
  "incident_ref": "INC-2026-0315",
  "external_ref": "SDP-2026-4421",
  "workspace_url": "https://irpdoc.company.com/incidents/uuid..."
}
```

This same endpoint works for any tool that can make HTTP POST requests: ServiceNow, ManageEngine, Jira, Freshservice, custom scripts. No special SDK or plugin required on the caller side.

### 7.4 Pluggable Storage Backend

All file I/O in the application goes through a single `StorageBackend` protocol. The active backend is configured once per organization in admin settings. SHA-256 is always computed during the upload stream and stored in the database — independently of where the file lives. Even if files are moved between backends, forensic integrity of existing evidence is preserved.

```python
class StorageBackend(Protocol):
    async def store(self, data: bytes, path: str) -> str: ...
    async def retrieve(self, path: str) -> bytes: ...
    async def delete(self, path: str) -> None: ...
    async def get_url(self, path: str, expires_in: int = 3600) -> str: ...
    async def test_connection(self) -> bool: ...
```

| Backend | Tier | Notes |
|---|---|---|
| `LocalStorageBackend` | Core | Files on Docker volume at `STORAGE_PATH` |
| `S3StorageBackend` | Premium | Covers AWS S3, MinIO, Cloudflare R2, Wasabi — same S3 API |
| `AzureBlobStorageBackend` | Premium | Azure Storage SDK |
| `GCSStorageBackend` | Premium | Google Cloud Storage SDK |

Network shares (SMB/NFS) work with local storage — mount the share as a Docker volume, point `STORAGE_PATH` at it. No special code needed.

---

## 8. Deployment Philosophy

### Single-command local start (developer):
```bash
git clone https://github.com/irp-platform/irp
cd irp && cp .env.example .env
docker compose up
# → App at http://localhost:3000
```

### Production (self-hosted):
```bash
docker compose -f docker-compose.prod.yml up -d
# Nginx terminates SSL, serves React build, proxies /api to FastAPI
```

### Upgrade:
```bash
docker compose pull && docker compose up -d
# Alembic migrations run automatically on backend container startup
```

No manual SQL. No manual file moves. One command to update.

---

## 9. API Design Philosophy

- All routes versioned under `/api/v1/...`
- Consistent response envelope: `{ data: ..., meta: { page, total }, error: null }`
- **Two authentication methods:**
  - **JWT** — user sessions. Access token (15 min, in-memory on frontend) + refresh token (30 days, HttpOnly cookie)
  - **API Key** — service-to-service. `Authorization: ApiKey irp_key_xxx`. Used by inbound webhook callers. Keys are org-scoped, permission-scoped, and hashed in the database
- All writes produce audit log entries (premium: stored in DB; core: logged to stdout only)
- OpenAPI docs auto-generated at `/api/docs`
- The external inbound API (`/api/v1/external/...`) is separately documented for service desk integrators

---

## 10. Security Considerations (Non-Negotiable from Day 1)

- All endpoints require authentication — no anonymous access anywhere
- API keys: hashed in DB (Argon2id), never returned after creation, minimum-permission scopes
- Inbound webhook endpoint: separate rate limit (20 req/min per key), payload size limit 64KB
- File uploads: MIME type validated, size limited (default 50MB, configurable), stored outside web root
- SHA-256 computed during upload stream — stored in DB independently of storage backend
- Served via signed/expiring URLs regardless of backend (local uses a signed token endpoint)
- Password hashing: Argon2id
- CORS locked to configured origin
- All SQL through ORM — no raw string queries
- Storage backend credentials encrypted at rest (Fernet symmetric encryption)
- Dependency scanning in CI (pip-audit, npm audit)
- Secrets only in `.env` — never in code, logs, or responses

---

## 11. What Phase 0 Delivers (Checklist)

- [ ] This document agreed upon by all stakeholders
- [ ] Git repositories created and initialized
- [ ] `.env.example` complete for both services
- [ ] `docker-compose.yml` skeleton with all services defined
- [ ] README.md with project vision, stack, quickstart
- [ ] GitHub Actions CI skeleton (lint + test on PR)
- [ ] LICENSE files committed (AGPL-3.0 + commercial)
- [ ] Design system documented (tokens from prototype → Tailwind config)
- [ ] Report template block schema format agreed and documented
- [ ] StorageBackend protocol interface agreed
- [ ] Inbound webhook API field contract sketched
- [ ] SharePoint debounce strategy confirmed (60s default, configurable)
- [ ] Team roles assigned

---

## 12. Roles Involved in This Phase

| Role | Responsibility |
|---|---|
| **Product Owner** | Approve vision, licensing, MVP scope, report template UX direction |
| **Architect** | Finalize stack, data model, plugin system, StorageBackend protocol, report block schema format |
| **Lead Developer** | Validate stack is buildable, set up repo scaffolding |
| **Designer** | Extract design tokens; sketch report builder UI and storage admin UI |
| **DevOps** | Docker compose structure, CI/CD skeleton |

---

*Next: Phase 1 — Foundation: Auth, Database, and Core Backend*
