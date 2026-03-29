# CLAUDE.md — IRDoc Build Reference

> This file is the authoritative instruction set for building IRDoc from Phase 0 to production launch.
> Read this before touching any code. Update it if architectural decisions change.

---

## 1. What We Are Building

**IRDoc** — a self-hostable, open-core Incident Response Documentation Platform.

**Product name:** IRDoc
**Target users:** SOC analysts, IR engineers, MSSPs
**Core promise:** "Document incidents the way you actually investigate them — fast, structured, and reportable in one click."
**Repo root folder name:** `irp-platform/` (local), project folder is `incident-response-platform/`

---

## 2. Open-Core Licensing (Non-Negotiable)

| Layer | License | Features |
|---|---|---|
| **Core** | AGPL-3.0 | Timeline, IOCs, Evidence, Tasks, Basic Report Export (Markdown/HTML), Inbound Webhook API, Local Storage, REST API |
| **Premium** | Commercial key | Report Template Builder, PDF/DOCX export, AI summaries, SharePoint auto-sync, Cloud storage (S3/Azure/GCS), Advanced integrations, Multi-tenancy, SSO/SAML, Audit logs, Custom branding |

**Rule:** Premium features are always visible in the UI with a `PremiumGate` lock overlay — never a 404. Users see what they would get, which motivates upgrading.

---

## 3. Confirmed Tech Stack (Do Not Change Without Explicit Instruction)

### Backend
- **Python 3.12 + FastAPI** (async, OpenAPI auto-docs)
- **SQLAlchemy 2 ORM + Alembic** (all DB access goes through ORM — NO raw SQL strings)
- **Pydantic v2** (request/response validation)
- **PostgreSQL 16** (JSONB for metadata/templates/enrichment, `tsvector` for FTS)
- **Redis 7** (Celery broker, pub/sub, debounce locks, session cache)
- **Celery** (async report generation, enrichment, sync, notifications)
- **Jinja2** (report rendering engine — block partials)
- **WeasyPrint** (HTML → PDF, no Chrome/Puppeteer)
- **python-docx** (DOCX export — premium only)
- **Argon2id** (password hashing AND API key hashing)
- **Fernet** (symmetric encryption for stored integration credentials + storage configs)
- **python3-saml** (SAML 2.0 SSO — Phase 5)
- **networkx** (graph layout computation — Phase 4)
- **bleach** (HTML sanitization in reports)
- **slowapi** (rate limiting)

### Frontend
- **React 18 + TypeScript**
- **Vite** (build tool)
- **Tailwind CSS** (utility-first — design tokens map to CSS variables from prototype)
- **Zustand** (UI state + auth — access token in-memory only, never localStorage)
- **TanStack Query / React Query** (server state, caching)
- **React Router v6** (SPA routing)
- **@dnd-kit/core** (drag-and-drop: report builder canvas, task reordering)
- **Socket.io client** (WebSocket real-time collaboration)
- **@xyflow/react (React Flow)** (investigation graph — Phase 4)
- **@tanstack/react-virtual** (timeline virtualization when > 100 entries)
- **Axios** (HTTP client with refresh interceptor)
- **Fonts:** Syne (display) + JetBrains Mono (mono) — from Google Fonts

### Infrastructure
- **Docker + Docker Compose** (primary deployment target)
- **Nginx** (reverse proxy, serves React build, proxies /api and /socket.io)
- **GitHub Actions** (CI/CD)

---

## 4. Repository Structure

```
irp-platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── incidents.py, timeline.py, iocs.py, evidence.py
│   │   │   ├── tasks.py, reports.py, report_templates.py
│   │   │   ├── users.py, integrations.py, storage.py
│   │   │   └── external.py          # Inbound webhook (SDP, ManageEngine, Jira)
│   │   ├── core/                    # Config, security, feature flags, permissions
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── schemas/                 # Pydantic schemas
│   │   ├── services/
│   │   │   ├── storage/             # StorageBackend adapters (base, local, s3, azure_blob, gcs)
│   │   │   └── report_renderer/     # Schema-driven Jinja2 engine + block renderers
│   │   ├── workers/                 # Celery tasks
│   │   └── plugins/                 # Integration adapters (pluggable registry)
│   ├── templates/reports/           # Jinja2 partials (blocks/ + base.html)
│   ├── alembic/
│   ├── tests/
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/              # layout/, timeline/, ioc/, summary/, reports/, integrations/, settings/, common/
│   │   ├── pages/                   # LoginPage, IncidentListPage, IncidentWorkspacePage
│   │   ├── hooks/                   # useIncident, useTimeline, useIOCs, useTasks, etc.
│   │   ├── stores/                  # authStore, themeStore, uiStore (Zustand)
│   │   ├── lib/                     # apiClient, websocket, iocDetector, utils
│   │   ├── types/
│   │   └── styles/                  # global.css with CSS variables (dark + light)
│   └── Dockerfile
├── docker/
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── nginx/nginx.conf
├── docs/
├── .github/workflows/
├── LICENSE                          # AGPL-3.0
├── LICENSE-COMMERCIAL.md
└── README.md
```

---

## 5. The Build Phases (Overview)

| Phase | Goal | Key Output |
|---|---|---|
| **0** | Vision + Architecture | This document, repo scaffold, docker-compose skeleton |
| **1** | Foundation Backend | Auth, DB schema, all CRUD APIs, StorageBackend, inbound webhook, Celery |
| **2** | Frontend React App | Pixel-faithful React port of HTML prototype, wired to real API, WebSocket |
| **3** | Reports + AI | Report template builder, PDF/DOCX/Markdown generation, AI summaries |
| **4** | Integrations + Graph | VT/AbuseIPDB enrichment, SharePoint sync, Sentinel/CrowdStrike, investigation graph |
| **5** | Multi-Tenancy + Enterprise | RBAC, invites, SSO/SAML, audit log, cloud storage backends, MSSP mode |
| **6** | Hardening + Launch | OWASP audit, perf targets, Docker Hub, CI/CD, docs, public launch |

---

## 6. The Full Database Schema (Phase 1 — Do Not Drift)

Tables (all UUIDs as PKs, all in PostgreSQL 16):

- `organizations` — id, name, slug, plan (core/pro/enterprise), license_key, settings JSONB
- `users` — id, org_id, email, full_name, role (admin/senior_analyst/analyst/viewer), password_hash (argon2id), timezone, theme, is_active
- `api_keys` — id, org_id, key_prefix (shown in UI), key_hash (argon2id, never plain), scopes TEXT[], expires_at
- `incident_templates` — id, org_id (null=system), name, slug, is_system, tasks_json JSONB
- `incidents` — id, org_id, incident_ref (INC-YYYY-NNNN), title, severity (sev1-4), status (open/contained/closed/monitoring), executive_summary, attack_vector TEXT[], affected_users, metadata JSONB
- `incident_external_refs` — id, incident_id, external_source, external_ref, external_url; UNIQUE(incident_id, external_source)
- `timeline_entries` — id, incident_id, author_id, entry_type (detection/analysis/containment/evidence/comms/note), occurred_at, description, source, is_pinned, metadata JSONB
- `attachments` — id, org_id, incident_id, timeline_entry_id, sha256 (ALWAYS stored in DB), stored_path, mime_type, storage_backend
- `iocs` — id, incident_id, ioc_type (email/domain/ip/url/hash/file/username), value, confidence 0-100, status (active/blocked/remediated/fp), enrichment JSONB, tlp_level, tags TEXT[]
- `ioc_timeline_links` — ioc_id, timeline_entry_id (M2M)
- `tasks` — id, incident_id, title, phase, priority, status, sort_order
- `report_templates` — id, org_id (null=system), name, destination (management/analyst/legal/custom), is_system, schema_json JSONB (ordered block array)
- `reports` — id, incident_id, report_template_id, format (pdf/docx/markdown/html), status (pending/generating/ready/failed), storage_path
- `sync_policies` — id, incident_id, destination, report_template_id, debounce_seconds (default 60), destination_config JSONB (encrypted), last_synced_at, last_sync_status
- `storage_configs` — id, org_id UNIQUE, backend (local/s3/azure_blob/gcs), config JSONB (encrypted), is_active
- `audit_log` — id BIGSERIAL, org_id, user_id, api_key_id, action, entity_type, entity_id, diff JSONB, ip_address INET
- `org_integrations` — id, org_id, plugin_name, is_enabled, config JSONB (encrypted); UNIQUE(org_id, plugin_name)
- `user_invites` — id, org_id, email, role, token, accepted_at, expires_at (+48h)

**Indexes:** All major foreign keys and filter columns are indexed. Full-text index on `timeline_entries.description`. Never add a query without checking EXPLAIN ANALYZE.

---

## 7. Key Architectural Rules (Never Violate)

### 7.1 StorageBackend Protocol
ALL file I/O goes through the `StorageBackend` protocol — never touch the filesystem directly.

```python
class StorageBackend(Protocol):
    async def store(data: bytes, path: str) -> str: ...
    async def retrieve(path: str) -> bytes: ...
    async def delete(path: str) -> None: ...
    async def get_url(path: str, expires_in: int = 3600) -> str: ...
    async def test_connection() -> bool: ...
```

SHA-256 is **always** computed during the upload stream and stored in `attachments.sha256` — independently of which backend is active. This is forensic integrity. Never skip it.

Local backend serves files via signed token endpoint (`GET /api/v1/files/{token}`) — files are NEVER served directly from web root.

### 7.2 Report Template Architecture
Reports are **schema-driven**, NOT hardcoded Jinja2 templates. They are user-composed schemas stored as JSONB (`report_templates.schema_json`) — an ordered array of block definitions. The renderer iterates blocks and assembles Jinja2 partials.

Block types: `cover`, `section`, `stat_row`, `timeline`, `ioc_table`, `task_list`, `evidence_register`, `text_block`, `divider`, `page_break`, `header`, `tag_list`

Adding a new block type = new Jinja2 partial + renderer entry. No DB migration. No frontend rebuild.

Three system templates ship by default: Management Brief, Technical Report, Legal/Compliance.

### 7.3 SharePoint Debounce Pattern
Any write to an incident calls `trigger_debounced_sync(incident_id)`. This sets a Redis key with TTL (default 60s). If the key already exists, TTL resets (debounce). After TTL expires, Redis keyspace notification fires → Celery task `sync_to_sharepoint` runs.

Redis **must** have `notify-keyspace-events Ex` enabled for this to work.

### 7.4 Inbound Webhook API
`POST /api/v1/external/incidents` — authenticated via API key (not JWT). Any tool that can POST JSON can create IRDoc cases. External ref (SDP ticket #, Jira issue, etc.) is stored in `incident_external_refs` and displayed throughout the UI.

### 7.5 Integration Plugin System
```python
@register_plugin
class SomePlugin:
    name = "..."
    category = "ti|siem|edr|iam|comms|email|storage_sync"
    is_premium = True|False
    config_schema = { ... }  # Frontend renders this as a form dynamically
```

New integration = new plugin file only. Never touch core code.

### 7.6 Feature Flags
`GET /api/v1/features` returns the full feature flag map for the org. Check `check_license("feature_group")` before any premium operation. Frontend uses `useFeatureFlags()` hook + `PremiumGate` component.

---

## 8. API Design Rules

- All routes under `/api/v1/...`
- Consistent envelope: `{ data: ..., meta: { page, total }, error: null }`
- **Two auth methods:**
  - **JWT** — user sessions. Access token (15 min, in-memory in Zustand). Refresh token (30 days, HttpOnly cookie).
  - **API Key** — service-to-service. `Authorization: ApiKey irp_key_xxx`. Keys hashed with argon2id in DB.
- OpenAPI docs at `/api/docs`
- All routes require authentication — no anonymous access

---

## 9. Security Rules (Non-Negotiable from Day 1)

- **All SQL through SQLAlchemy ORM** — zero raw string queries
- **Argon2id** for all password + API key hashing
- **Fernet** for all credentials stored in DB (integration configs, storage configs)
- **API keys** hashed in DB — never stored plain, shown only once at creation
- **File uploads:** MIME validated, 50MB max (configurable), UUID paths, outside web root
- **JWT:** access token in Zustand memory only (not localStorage), refresh in HttpOnly SameSite=Strict cookie
- **CORS:** locked to configured BASE_URL origin
- **Rate limits:** auth 5/min, inbound webhook 20/min per key, general API 100/min
- **Secrets** only in `.env` — never in code, logs, responses, or exception messages
- **Inbound webhook payload** max 64KB
- **Destructive actions** (contain host, revoke sessions) require confirmation modal + Senior Analyst/Admin role + audit log with HIGH risk flag
- **OWASP Top 10** addressed from Phase 1 — not an afterthought in Phase 6
- **Security headers** via Nginx: HSTS, X-Frame-Options DENY, nosniff, CSP

---

## 10. Frontend Rules

- **Access token** stored in Zustand (memory only) — NEVER in localStorage
- **Theme** persisted to localStorage (dark/light)
- **Design tokens** from HTML prototype CSS variables → Tailwind config → `src/styles/global.css`
- **Fonts:** Syne (display) + JetBrains Mono (mono)
- **Theme switching:** `data-theme` attribute on `<html>` — same as prototype
- **Optimistic updates** on timeline entry submission. Roll back on failure with toast.
- **401 handling:** Axios interceptor calls `/auth/refresh`. On success: retry. On failure: clear store, redirect to login.
- **Code splitting:** Vite route-based. Heavy components (React Flow graph, report builder) lazy-loaded.
- **Timeline virtualization** when > 100 entries (`@tanstack/react-virtual`)
- **Bundle target:** < 200KB gzipped initial load
- **PremiumGate** wraps ALL premium UI — content renders but is dimmed + locked. Never hide it entirely.
- **Keyboard shortcuts:** `N` focuses Add Entry form, `Escape` closes modals
- **All icon-only buttons** have `aria-label`
- **Color is never the only meaning carrier** — badges always include text

---

## 11. WebSocket Events

Server → Client:
- `timeline:entry:added` / `updated` / `deleted`
- `task:updated`
- `ioc:added` / `ioc:enriched` (Phase 4)
- `incident:updated`
- `report:ready`
- `sync:complete` `{ policy_id, url }`

Client → Server:
- `join:incident` / `leave:incident`

---

## 12. Service Layer Structure (Backend)

Routes are **thin**. All business logic in `services/`:
- `incident_service` — create, update, soft-delete, stats, ref generation (`INC-YYYY-NNNN`)
- `timeline_service` — CRUD + auto-link IOC mentions
- `ioc_service` — CRUD + auto-type detection regex
- `attachment_service` — stream upload, compute sha256, delegate to StorageBackend
- `task_service` — instantiate from template, progress calc
- `template_service` — CRUD + seed system templates
- `auth_service` — JWT, password hashing, refresh tokens
- `api_key_service` — key creation (argon2id hash), verification, scope check
- `external_service` — inbound webhook logic
- `storage_service` — backend resolution, config management
- `report_service` — payload building, rendering, storage
- `ai_service` — provider-agnostic (Anthropic/OpenAI/Ollama) via Protocol

---

## 13. Celery Workers

Key tasks (in priority order of implementation):
1. `verify_file_hash(attachment_id)` — re-verify SHA-256 after storage
2. `auto_detect_iocs_from_entry(entry_id)` — scan description, surface suggestions
3. `generate_report(report_id)` — full report pipeline
4. `enrich_ioc(ioc_id)` — multi-provider enrichment
5. `sync_to_sharepoint(incident_id, policy_id)` — debounced sync with 3 retries
6. `generate_ai_summary(incident_id)` — Anthropic/OpenAI/Ollama
7. `generate_ai_recommendations(incident_id)`
8. `send_notification(org_id, event, payload)` — Slack/Teams

Debounce lock pattern: `redis.set(f"sync_pending:{incident_id}:{policy_id}", value, ex=debounce_seconds)` — reset TTL on each change, fire sync on expiry.

---

## 14. IOC Auto-Detection Regex (Client + Server)

Both backend (`ioc_service.auto_detect()`) and frontend (`lib/iocDetector.ts`) implement the same patterns:
- IP: `\b(?:\d{1,3}\.){3}\d{1,3}\b`
- Email: `\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b`
- MD5: `\b[a-fA-F0-9]{32}\b`
- SHA1: `\b[a-fA-F0-9]{40}\b`
- SHA256: `\b[a-fA-F0-9]{64}\b`
- URL: `https?://[^\s<>"{}|\\^` + "`" + `\[\]]+`

When user pastes multi-line text into IOC field → show auto-detect modal: "We found N IOCs — add all?"

---

## 15. RBAC (Phase 5)

Roles: `admin` > `senior_analyst` > `analyst` > `viewer`

Key permission boundaries:
- **Viewer:** read-only everywhere, can generate reports
- **Analyst:** create/edit own entries, add IOCs, create incidents
- **Senior Analyst:** + delete any entry, close incidents, manage templates, manage sync policies, containment actions
- **Admin:** everything + users, API keys, integrations, storage config, audit log

FastAPI: `require_permission("permission.name")` dependency on routes. Never rely on frontend-only permission hiding.

---

## 16. Environment Variables (Key Ones)

```env
DATABASE_URL=postgresql+asyncpg://irp:...@db/irp
REDIS_URL=redis://:...@redis:6379/0
SECRET_KEY=<openssl rand -hex 32>
STORAGE_BACKEND=local
STORAGE_PATH=/app/storage
BASE_URL=http://localhost:3000
LICENSE_KEY=                    # empty = core only
WEBHOOK_RATE_LIMIT=20
WEBHOOK_MAX_PAYLOAD_BYTES=65536
AI_BACKEND=anthropic            # anthropic | openai | ollama
AI_MODEL=claude-sonnet-4-6
ALLOW_REGISTRATION=true
EMAIL_BACKEND=console
```

---

## 17. Seed Data (Phase 1, runs on first start)

1. Default org (`slug: default`)
2. Admin user (`admin@localhost`, force-reset on first login)
3. 4 system incident templates: phishing, credential-compromise, malware-infection, suspicious-login
4. 3 system report templates: Management Brief, Technical Report, Legal/Compliance

---

## 18. Performance Targets (Phase 6 Gate)

| Endpoint | P50 | P95 |
|---|---|---|
| GET /incidents | < 50ms | < 100ms |
| GET /incidents/{id}/timeline | < 80ms | < 150ms |
| POST /timeline | < 100ms | < 200ms |
| GET /incidents/{id}/graph | < 200ms | < 400ms |
| POST /external/incidents | < 150ms | < 300ms |

Load test: 20 concurrent analysts, 5 active incidents, 30 minutes — zero 5xx errors.

---

## 19. Investigation Graph (Phase 4)

- Library: `@xyflow/react` (React Flow)
- Node types: user, host, IOC (ip/domain/email/url/hash), alert, evidence, key event
- Layout computed server-side with `networkx` (hierarchical)
- Node colors follow existing status color system
- Features: pan/zoom/minimap, click node → detail panel, export SVG/PNG, manual edge creation
- API: `GET /api/v1/incidents/{id}/graph` returns `{ nodes, edges }` with dagre positions

---

## 20. CI/CD Pipeline (Phase 6)

On PR to main:
1. `pip-audit` — fail on high/critical vulnerabilities
2. `ruff check` — backend linting
3. `pytest --cov=app` — 80%+ coverage required
4. Secret leak grep: `grep -r "irp_key_\|sk-ant-\|AKIA"` must be clean
5. `npm audit --audit-level=high`
6. `tsc --noEmit` (type check)
7. `eslint`
8. `npm run build`

On merge to main → build + push multi-arch Docker images (amd64 + arm64).

---

## 21. Upgrade Safety Rule

Every Alembic migration must be backward-compatible with the previous image version:
- No column drops
- No NOT NULL additions without defaults
- No table renames in a single migration

Two-migration approach for breaking changes. This enables zero-downtime rolling upgrades.

---

## 22. What to Never Do

- Never write raw SQL strings — always ORM
- Never store secrets in code, logs, or API responses
- Never store access tokens in localStorage (Zustand memory only)
- Never serve files directly from web root (always signed URLs)
- Never skip SHA-256 computation on file upload
- Never use `docker compose -f docker-compose.prod.yml push --force` without explicit user approval
- Never add a feature for a later phase when building an earlier phase
- Never modify system templates (org_id=null) — they are read-only; orgs must clone
- Never expose raw integration credentials via API response — redact always
- Never deploy without migrations running on startup (`entrypoint.sh`)
- Never add DOCX/PDF export without checking `check_feature("report_pdf_export")`

---

## 23. Three-File Reference Chain

For deep detail on any phase:
- `_info/IRP_Phase_0_Vision_and_Architecture.md` — foundational decisions
- `_info/IRP_Phase_1_Foundation_Backend.md` — complete DB schema + all Phase 1 APIs
- `_info/IRP_Phase_2_Frontend_React.md` — component structure + auth flow + real-time
- `_info/IRP_Phase_3_Reports_and_AI.md` — report template architecture + AI providers
- `_info/IRP_Phase_4_Integrations_and_Graph.md` — all plugins + SharePoint worker + graph
- `_info/IRP_Phase_5_MultiTenancy_and_Enterprise.md` — RBAC + SSO + cloud storage + MSSP
- `_info/IRP_Phase_6_Hardening_and_Launch.md` — OWASP checklist + perf + CI/CD + docs

---

## 24. Current Status

**Phase 0** — Complete. Architecture documented.
**Phase 1** — Complete. Full backend foundation built and tested.
**Phase 2** — Complete. React 18 + TypeScript frontend built and wired to API.
**Phase 3** — Complete. Report Template Builder, PDF/DOCX/Markdown/HTML generation, AI summaries, Sync Policy UI.
**Phase 4** — Complete. IOC Enrichment (VT/AbuseIPDB/Shodan), integration plugins, SharePoint sync worker, React Flow investigation graph.
**Phase 5** — Complete. RBAC, user invites, SSO/SAML, audit log, cloud storage backends (S3/Azure/GCS), admin panel.
**Phase 6** — Complete. Security hardening, CI/CD, production Docker Compose, upgrade/backup scripts, README, CHANGELOG, docs.

**Project status:** All 7 phases complete. Ready for public launch at v1.0.0.

**Post-launch additions:**
- **Assets feature** — DB migration 004, full backend + frontend implementation. See Section 31.

**Next action:** Tag v1.0.0, publish Docker Hub images, make GitHub repository public. Refer to Section 30.

---

## 25. Phase 1 — Implementation Reference (What Was Actually Built)

> Read this section before touching any Phase 1 code. It captures decisions made during implementation that are not obvious from the spec alone.

### 25.1 Repository Layout (As Built)

```
incident-response-platform/
├── .env.example                  # Copy to .env before running
├── .gitignore
├── CLAUDE.md
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh             # Runs migrations + seed on container start
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── pyproject.toml            # ruff config
│   ├── pytest.ini
│   ├── seed.py                   # Run standalone or via entrypoint
│   ├── alembic/
│   │   ├── env.py                # Async Alembic setup
│   │   └── versions/
│   │       └── 001_initial_schema.py   # All Phase 1 tables + indexes
│   ├── app/
│   │   ├── main.py               # FastAPI app, routers, CORS, security headers
│   │   ├── api/v1/               # Thin route handlers only
│   │   │   ├── auth.py, api_keys.py, incidents.py, timeline.py
│   │   │   ├── attachments.py, iocs.py, tasks.py, templates.py
│   │   │   ├── external.py, features.py
│   │   ├── core/
│   │   │   ├── config.py         # Pydantic Settings (lru_cache singleton)
│   │   │   ├── database.py       # AsyncEngine + get_db() dependency
│   │   │   ├── security.py       # JWT, argon2id, API key, signed file tokens
│   │   │   ├── permissions.py    # RBAC — require_permission() FastAPI dep
│   │   │   ├── feature_flags.py  # check_feature() + get_all_flags()
│   │   │   └── debounce.py       # Redis TTL debounce for sync
│   │   ├── models/               # SQLAlchemy 2 ORM (all import in __init__.py)
│   │   ├── schemas/              # Pydantic v2 (request + response)
│   │   ├── services/             # All business logic lives here
│   │   │   ├── storage/
│   │   │   │   ├── base.py       # StorageBackend Protocol
│   │   │   │   ├── local.py      # LocalStorageBackend
│   │   │   │   └── resolver.py   # get_storage_backend() — lru_cache
│   │   └── workers/
│   │       ├── celery_app.py     # Celery config + beat schedule
│   │       └── tasks.py          # verify_file_hash (live), stubs for Phase 3/4
│   └── tests/
│       ├── conftest.py           # SQLite in-memory fixtures + auth_headers
│       ├── unit/                 # IOC regex, SHA-256, API key, storage
│       └── integration/          # auth, incidents, timeline, IOCs, webhook
├── docker/
│   ├── docker-compose.yml        # NOTE: lives in docker/, not root
│   └── nginx/nginx.conf
├── frontend/                     # Empty — Phase 2
└── storage/                      # File uploads (gitignored, mounted as volume)
```

### 25.2 Critical Implementation Patterns

**SQLAlchemy `metadata` column naming:**
PostgreSQL column is named `metadata` but SQLAlchemy ORM attribute is `metadata_` (avoids conflict with SQLAlchemy's own `.metadata`). The Pydantic schemas handle this via `model_validate` override that copies `metadata_` → `metadata`. This affects `Incident` and `TimelineEntry` models.

**API response envelope:**
All endpoints return `{ "data": ..., "meta": {...}, "error": null }`. The `meta` field carries pagination (`page`, `per_page`, `total`). Never return bare objects from endpoints — always wrap.

**RBAC dependency pattern:**
```python
current_user = Depends(require_permission("incidents.read"))
```
Permission strings are in `app/core/permissions.py:PERMISSIONS`. Always use `require_permission()` on routes, not `get_current_user()` directly (except auth routes).

**Inbound webhook auth pattern:**
External routes use `Depends(require_scope("incidents:create"))` — this validates an API key, NOT a JWT. The `Authorization` header format is `ApiKey irp_key_xxxx`, not `Bearer`.

**StorageBackend resolver is cached:**
`get_storage_backend()` in `resolver.py` uses `@lru_cache`. If storage backend config changes at runtime (Phase 5), must call `get_storage_backend.cache_clear()`.

**Incident ref generation:**
Uses PostgreSQL sequences: `incident_seq_{org_id_no_dashes}_{year}`. Created on-demand if not exists. Produces `INC-YYYY-NNNN`. Thread-safe.

**Celery task → async bridge:**
Celery workers are sync. Use `run_async(coro)` helper in `tasks.py` to bridge to async DB calls. Each task creates its own event loop.

**File token signing:**
`sign_file_token(path, expires_in)` in `security.py`. Token = base64(path:expire_timestamp:hmac_sha256). Used by `GET /api/v1/files/{token}`. Tokens expire — re-request URL if you get 403.

### 25.3 Docker Compose Location

`docker-compose.yml` is in `docker/`, NOT at the project root. To start:
```bash
cp .env.example .env   # edit SECRET_KEY, DB_PASSWORD, REDIS_PASSWORD
cd docker
docker compose up
```

The compose file uses `build: context: ../backend` (relative to `docker/`).

### 25.4 Seed Data

Runs automatically via `entrypoint.sh` on first start (skips if org `slug=default` already exists).

| Item | Value |
|---|---|
| Admin email | `admin@localhost` |
| Admin password | `ChangeMe123!` |
| Must reset on login | `true` |
| Incident templates | phishing, credential-compromise, malware-infection, suspicious-login |
| Report templates | Management Brief (default), Technical Report, Legal/Compliance |

System templates have `org_id = NULL` and `is_system = true`. They are read-only — users must clone.

### 25.5 API Key Scopes (Exact Strings)

```
incidents:create   incidents:read   incidents:write
timeline:read      iocs:read        reports:read
```

The inbound webhook requires `incidents:create`. Scope validation is in `api_key_service.py:VALID_SCOPES`.

### 25.6 IOC Auto-Detection Notes

- Detection order matters: url → email → sha256 → sha1 → md5 → ip → domain
- SHA-1, SHA-256, MD5 all map to `ioc_type = "hash"` (not "sha256" etc.) — matches frontend display
- Email regex runs before domain to avoid domain being extracted from email addresses
- `auto_detect()` deduplicates by value before returning
- Used in both `ioc_service.py` (server) and will be in `lib/iocDetector.ts` (client) — **keep patterns in sync**

### 25.7 Permissions Quick Reference

| Permission string | Minimum role |
|---|---|
| `incidents.read` | viewer |
| `incidents.create` | analyst |
| `incidents.update` | analyst |
| `incidents.delete` | senior_analyst |
| `incidents.close` | senior_analyst |
| `timeline.read` | viewer |
| `timeline.create` | analyst |
| `timeline.delete_any` | senior_analyst |
| `timeline.pin` | senior_analyst |
| `iocs.create` | analyst |
| `tasks.update` | analyst |
| `templates.create` | senior_analyst |
| `api_keys.manage` | admin |
| `users.manage` | admin |
| `audit_log.read` | admin |

### 25.8 Test Setup Notes

- Unit tests: pure Python, no DB — run instantly
- Integration tests: use SQLite in-memory via `conftest.py` (no PostgreSQL needed for local dev)
- `aiosqlite` must be installed for SQLite async tests — add to `requirements.txt` if missing
- `auth_headers` fixture performs a real login and returns `{"Authorization": "Bearer <token>"}`
- The `admin_user` fixture creates org + user in the test DB session

### 25.9 Phase 1 Checklist (All Complete)

- [x] PostgreSQL schema + Alembic migration 001
- [x] Seed: org, admin, 4 incident templates, 3 report templates
- [x] FastAPI app with all routers registered
- [x] Auth: register, login, refresh (cookie), logout, me, setup, change-password
- [x] API key: create (argon2id hash, show raw once), list, revoke
- [x] Incidents: CRUD + ref generation + external refs + stats
- [x] Timeline: CRUD + CSV export + pin/unpin
- [x] Attachments: upload + SHA-256 + StorageBackend + signed URL serving
- [x] IOCs: CRUD + auto-detect + bulk import + detect-only endpoint
- [x] Tasks: CRUD + template instantiation
- [x] Templates: incident + report (system + org-level)
- [x] Features endpoint: `GET /api/v1/features`
- [x] Inbound webhook: `POST /api/v1/external/incidents`
- [x] Celery: `verify_file_hash` (live), `auto_detect_iocs_from_entry` (live), stubs for Phase 3/4
- [x] Debounce lock utility (Redis-based, beat task polling)
- [x] Health endpoint: `GET /api/health`
- [x] RBAC enforced server-side on all routes
- [x] Feature flags enforced via `check_feature()`
- [x] Security headers middleware
- [x] Unit tests: IOC regex, storage, API key, file tokens
- [x] Integration tests: auth, incidents, timeline, IOCs, webhook

---

## 26. Phase 2 — Implementation Reference (What Was Actually Built)

> Read this before touching any Phase 2 (frontend) code.

### 26.1 Frontend Repository Layout (As Built)

```
frontend/
├── Dockerfile                  # Multi-stage: node:20-alpine builder → nginx:alpine
├── nginx.conf                  # SPA fallback + /api and /socket.io proxy
├── package.json                # React 18, Vite, Tailwind, Zustand, TanStack Query, Socket.io
├── tsconfig.json               # strict, path alias @/ → src/
├── vite.config.ts              # proxy /api → :8000, proxy /socket.io → :8000 (ws)
├── tailwind.config.js          # CSS variables mapped to Tailwind colors
├── postcss.config.js
├── index.html                  # Fonts loaded here (Syne + JetBrains Mono)
└── src/
    ├── main.tsx                # QueryClient + BrowserRouter + StrictMode
    ├── App.tsx                 # Routes + session restore on load + ToastContainer
    ├── styles/global.css       # All CSS variables (dark/light), base reset, utility classes
    ├── types/                  # api.ts, user.ts, incident.ts, timeline.ts, ioc.ts, task.ts, apiKey.ts
    ├── stores/                 # authStore.ts (access token in memory), themeStore.ts (localStorage), uiStore.ts
    ├── lib/                    # apiClient.ts, websocket.ts, iocDetector.ts, utils.ts
    ├── hooks/                  # useAuth, useIncident, useTimeline, useIOCs, useTasks, useFeatureFlags, useAPIKeys
    ├── components/
    │   ├── common/             # Badge, Button, Modal, Toast, LoadingSpinner, EmptyState, PremiumGate, ToggleSwitch, ExternalRefBadge, ProgressBar
    │   ├── layout/             # AppShell, LeftNav, TopBar, TasksPanel
    │   ├── timeline/           # TimelinePage, AddEntryForm, AttachmentZone, TimelineEntry, TimelineFilters
    │   ├── ioc/                # IOCPage, ConfidenceBar
    │   ├── summary/            # SummaryPage
    │   ├── reports/            # ReportPage (shell — functional in Phase 3)
    │   ├── integrations/       # IntegrationsPage (shell — functional in Phase 4)
    │   └── settings/           # SettingsPage, APIKeysSection
    └── pages/                  # LoginPage, IncidentListPage, IncidentWorkspacePage, SettingsPageWrapper
```

### 26.2 Critical Frontend Patterns

**Session restore on load:**
`App.tsx` calls `POST /auth/refresh` on mount. On success: stores token + user in Zustand. On failure: user stays unauthenticated, redirect to `/login`. This means the app always tries to restore the session silently before showing the login page.

**Access token never in localStorage:**
`useAuthStore` is a plain Zustand store (no persist middleware). Token lives only in memory. If the page is refreshed, the session is restored via the refresh cookie.

**401 refresh interceptor:**
`apiClient.ts` queues all requests that get 401 while refresh is in-flight (isRefreshing flag + refreshQueue array). After refresh succeeds, all queued requests are replayed. This is transparent to the user.

**Theme persistence:**
`themeStore.ts` uses `zustand/middleware persist` with key `irdoc-theme`. On rehydrate, applies `document.documentElement.setAttribute('data-theme', theme)`.

**IOC auto-detect on paste:**
In `IOCPage.tsx`, the IOC value input's `onPaste` handler checks if the pasted text is multi-line or long (>100 chars). If so, it runs `detectIOCs()` from `lib/iocDetector.ts` and opens a selection modal. The backend `/iocs/bulk` endpoint is used for the actual save (not the frontend regex — the backend re-detects to ensure consistency).

**Attachment upload flow:**
`AddEntryForm.tsx` first POSTs the timeline entry, gets back the entry ID, then loops over pending files and POSTs each to `/incidents/{id}/attachments` with `multipart/form-data` and `timeline_entry_id` in the form data.

**Global paste for screenshots:**
`AttachmentZone.tsx` adds a `document.addEventListener('paste', ...)` listener on mount. Any image pasted anywhere on the page (not just in a file input) is captured and added to the pending files list.

**Task toggle with optimistic update:**
`useTasks.ts:useUpdateTask` uses `onMutate` to immediately update the cache, `onError` to roll back, and `onSettled` to invalidate. Tasks panel shows changes instantly before the API responds.

**WebSocket room joining:**
`TimelinePage.tsx` calls `joinIncident(id)` on mount and `leaveIncident(id)` on unmount. Socket events `timeline:entry:added/updated/deleted` each call `qc.invalidateQueries({ queryKey: ['timeline', id] })` — no manual cache surgery needed.

**Keyboard shortcuts:**
`N` key → focus the Add Entry textarea (global listener in `TimelinePage.tsx`). `Escape` → close any modal (listener in `Modal.tsx`).

### 26.3 Design System Notes

All CSS variables defined in `src/styles/global.css` under `:root[data-theme="dark"]` and `:root[data-theme="light"]`. These are the exact values from the HTML prototype.

Key utility classes defined in `global.css` (NOT Tailwind utilities — hand-written to match prototype):
- `.form-input` — styled input/select/textarea
- `.btn`, `.btn-accent`, `.btn-ghost`, `.btn-danger`, `.btn-sm` — buttons
- `.icon-btn` — 28px icon-only button
- `.chip`, `.chip-red`, `.chip-green`, `.chip-blue`, `.chip-yellow`, `.chip-purple`, `.chip-muted` — status badges
- `.animate-slide-in`, `.animate-fade-in` — CSS keyframe animations
- `.select-wrap` — wrapper div that adds the dropdown arrow pseudo-element

### 26.4 Route Structure (As Implemented)

```
/                          → redirect → /incidents
/login                     → LoginPage (first-run setup + login)
/incidents                 → IncidentListPage (AppShell wraps it)
/incidents/:id             → IncidentWorkspacePage (default section: timeline)
/incidents/:id/:section    → IncidentWorkspacePage (section in state, not URL-driven)
/settings                  → SettingsPageWrapper → SettingsPage
```

Note: Section tabs (timeline/iocs/summary/reports/integrations) update React state, not URL params, to avoid full re-renders. Section is local state in `IncidentWorkspacePage`.

### 26.5 Docker Integration

Frontend service added to `docker/docker-compose.yml`:
- Build context: `../frontend`
- Exposes port 3000:80
- Depends on: backend
- Nginx serves the React build and proxies `/api` and `/socket.io` to the backend service

Dev mode (without Docker): `npm run dev` in `frontend/` starts Vite on port 3000. Vite's built-in proxy handles `/api` → `http://localhost:8000`.

### 26.6 Phase 2 Checklist (All Complete)

- [x] Vite + React 18 + TypeScript + Tailwind scaffold
- [x] CSS variables global.css (dark + light) — exact prototype colors
- [x] API client (Axios + 401 refresh interceptor with request queue)
- [x] Auth (Login page, first-run setup, token in memory, session restore)
- [x] Incident List page with status filter, search, external ref badges
- [x] AppShell (LeftNav + content wrapper)
- [x] LeftNav (icons, tooltips, logo, theme toggle, user avatar, logout)
- [x] TopBar (severity badge, ref, title, external refs, status, section tabs)
- [x] TasksPanel (grouped by phase, optimistic toggle, progress bar)
- [x] Timeline page (Add entry form + filters + timeline with vertical line)
- [x] AddEntryForm (auto-updating time, attachment zone, submit → upload)
- [x] AttachmentZone (drag/drop + global paste for screenshots)
- [x] TimelineEntry card (hover actions, pin, delete, lightbox for images)
- [x] IOC page (inline add form, table, auto-detect modal on multi-line paste)
- [x] Summary page (stat cards, incident details, editable executive summary)
- [x] Report page (shell — PremiumGate around PDF/DOCX cards)
- [x] Integrations page (shell — PremiumGate around premium integrations)
- [x] Settings page (profile, theme toggle, change password)
- [x] APIKeysSection (create with one-time raw key display, list, revoke)
- [x] Toast notification system (4s auto-dismiss, success/error/info)
- [x] PremiumGate component (dim + lock overlay + upgrade prompt)
- [x] WebSocket integration (join/leave room, invalidate query on events)
- [x] Theme toggle (persisted to localStorage via Zustand persist)
- [x] ExternalRefBadge component (SDP, Jira, ME, SN labels)
- [x] Frontend Dockerfile (multi-stage, nginx:alpine)
- [x] nginx.conf (gzip, /api proxy, /socket.io WS proxy, SPA fallback)
- [x] docker-compose.yml updated with frontend service

---

## 27. Phase 3 — Implementation Reference (What Was Actually Built)

> Read this section before touching any Phase 3 code.

### 27.1 New Backend Files

```
backend/
├── app/
│   ├── schemas/
│   │   └── report.py                    # ReportGenerateRequest, ReportOut, SyncPolicyCreate/Update/Out
│   ├── services/
│   │   ├── ai_service.py                # AIProvider protocol, Anthropic/OpenAI/Ollama providers, prompt builders
│   │   ├── sync_policy_service.py       # SyncPolicy CRUD (feature-gated)
│   │   ├── report_service.py            # enqueue_report, list/get/delete report
│   │   └── report_renderer/
│   │       ├── __init__.py
│   │       ├── payload.py               # ReportPayload dataclass + build_report_payload()
│   │       ├── engine.py                # ReportRenderer (Jinja2 → html/markdown/pdf/docx)
│   │       └── docx_builder.py          # python-docx premium builder
│   └── api/v1/
│       ├── reports.py                   # POST/GET/download/DELETE /incidents/{id}/reports + /reports/{id}
│       ├── report_templates.py          # Full CRUD + clone + preview (separate from templates.py)
│       ├── sync_policies.py             # CRUD + trigger stub /incidents/{id}/sync-policies
│       └── ai.py                        # POST /incidents/{id}/ai/summary + /recommendations
├── templates/reports/
│   ├── base.html                        # WeasyPrint-compatible HTML layout + print CSS
│   └── blocks/
│       ├── cover.html, stat_row.html, section.html, timeline.html
│       ├── ioc_table.html, task_list.html, evidence_register.html
│       ├── text_block.html, divider.html, page_break.html, header.html, tag_list.html
```

### 27.2 Key Backend Patterns

**ReportPayload:**
`build_report_payload(incident_id, analyst, db)` fetches all data (incident + refs + entries + IOCs + tasks + attachments) and pre-computes all derived fields (duration, counts, groupings by type/status/phase). All Jinja2 templates read only from `p` (the payload) — zero DB queries during rendering.

**Report generation pipeline (Celery `generate_report` task):**
1. Load Report + ReportTemplate + User from DB
2. Mark report `status="generating"`
3. Build `ReportPayload` via `build_report_payload()`
4. If `include_ai=True` and licensed: call AI provider for blocks that use `ai.*` field paths
5. Call `ReportRenderer.render(schema_json, payload, format)` → bytes
6. Store via `StorageBackend` at `reports/{incident_id}/{report_id}.{ext}`
7. Update report: `status="ready"`, `storage_path`, `generated_at`
8. Publish `report:ready` event to Redis pub/sub → WebSocket clients

**WebSocket report:ready delivery:**
Worker uses Redis pub/sub (`irp:ws:{incident_id}` channel) to notify. The FastAPI Socket.io layer subscribes to this channel and re-emits to connected incident room clients. Frontend `useReports` also polls every 3s while any report is `pending/generating`.

**AI service pattern:**
`get_ai_provider()` returns `AnthropicProvider`, `OpenAIProvider`, or `OllamaProvider` based on `AI_BACKEND` env var. All implement `async complete(system, user, max_tokens) -> str`. Prompt builders in `ai_service.py` — never inline in the task.

**Template clone:**
`clone_report_template()` in `template_service.py` creates an org-owned copy of any template (usually a system one). Name gets "(Copy)" suffix. `is_system=False`, `is_default=False`.

**Report template endpoints:**
New router `report_templates.py` provides the full suite (list, get, create, update, delete, clone, preview). The old `templates.py` still handles incident templates + basic report template CRUD — the new router adds clone/preview. Both are registered. No duplicate routes because `report_templates.py` uses `/report-templates/...` paths.

### 27.3 New Frontend Files

```
frontend/src/
├── types/report.ts                      # Report, ReportTemplate, ReportBlock, SyncPolicy types
│                                        # + BLOCK_LIBRARY, FORMAT_LABELS, DESTINATION_OPTIONS
├── hooks/
│   ├── useReports.ts                    # useReports (polls while pending/generating), useGenerateReport, useDeleteReport, useDownloadReport
│   ├── useReportTemplates.ts            # useReportTemplates, useReportTemplate, useCreate/Update/Delete/CloneReportTemplate
│   └── useSyncPolicies.ts               # useSyncPolicies, useCreate/Update/Delete/TriggerSyncPolicy
├── components/reports/
│   ├── ReportPage.tsx                   # FULL implementation (replaces Phase 2 shell)
│   ├── GenerateReportModal.tsx          # Format picker, classification, AI toggle
│   ├── SyncPolicySection.tsx            # List + add/delete/trigger + enable/disable
│   ├── ReportTemplateBuilder.tsx        # @dnd-kit canvas + block library panel
│   └── BlockConfigPanel.tsx             # Per-block-type inline config fields
└── pages/
    ├── ReportTemplateListPage.tsx       # /report-templates list with system vs org sections
    └── ReportTemplateEditorPage.tsx     # /report-templates/:id full-page builder
```

### 27.4 PremiumGate Update

`PremiumGate.tsx` was updated to:
- Accept **both** `feature` (existing Phase 2 prop) and `featureKey` (new Phase 3 alias) — same logic, either works
- Add a **default export** alongside the named export

This keeps all Phase 2 usages (`<PremiumGate feature="x">`) working while Phase 3 components use the more descriptive `featureKey`.

### 27.5 Route Changes

New routes added to `App.tsx`:
- `/report-templates` → `ReportTemplateListPage`
- `/report-templates/:id` → `ReportTemplateEditorPage` (full-page, no AppShell)

### 27.6 Sync Policy Notes

Sync policy UI is fully wired (create/update/delete/trigger). The `trigger` endpoint returns 202 with a stub message. Actual SharePoint delivery is Phase 4 (`sync_to_sharepoint` Celery task).

The `destination_config` JSONB field is where SharePoint credentials go — these will be Fernet-encrypted in Phase 4 when the full plugin is built.

### 27.7 Phase 3 Checklist (All Complete)

**Backend:**
- [x] `app/schemas/report.py` — ReportGenerateRequest, ReportOut, SyncPolicyCreate/Update/Out
- [x] `app/services/report_renderer/` — payload builder, Jinja2 engine, DOCX builder
- [x] `app/services/ai_service.py` — Anthropic/OpenAI/Ollama providers + prompt builders
- [x] `backend/templates/reports/` — base.html + 12 block partials
- [x] `app/services/report_service.py` — full enqueue/list/get/delete
- [x] `app/services/sync_policy_service.py` — full CRUD (premium-gated)
- [x] `app/services/template_service.py` — added `clone_report_template()`
- [x] `app/workers/tasks.py` — `generate_report` (full pipeline), `generate_ai_summary`, `generate_ai_recommendations`
- [x] `app/api/v1/reports.py` — enqueue, list, status, download, delete
- [x] `app/api/v1/report_templates.py` — full CRUD + clone + preview
- [x] `app/api/v1/sync_policies.py` — CRUD + trigger stub
- [x] `app/api/v1/ai.py` — summary + recommendations endpoints
- [x] `app/main.py` — all 4 new routers registered

**Frontend:**
- [x] `src/types/report.ts` — all types + BLOCK_LIBRARY constant
- [x] `src/hooks/useReports.ts` — with 3s poll while pending/generating
- [x] `src/hooks/useReportTemplates.ts` — CRUD + clone
- [x] `src/hooks/useSyncPolicies.ts` — CRUD + trigger
- [x] `src/components/reports/ReportPage.tsx` — fully functional (replaces shell)
- [x] `src/components/reports/GenerateReportModal.tsx` — format/classification/AI toggle
- [x] `src/components/reports/SyncPolicySection.tsx` — full UI
- [x] `src/components/reports/ReportTemplateBuilder.tsx` — @dnd-kit drag-and-drop canvas
- [x] `src/components/reports/BlockConfigPanel.tsx` — per-block config panels
- [x] `src/pages/ReportTemplateListPage.tsx` — system vs org template list
- [x] `src/pages/ReportTemplateEditorPage.tsx` — full-page builder
- [x] `src/components/common/PremiumGate.tsx` — updated to support `featureKey` alias
- [x] `src/App.tsx` — routes for /report-templates and /report-templates/:id
- [x] `src/pages/IncidentWorkspacePage.tsx` — updated import for new default export



---

## 28. Phase 4 — Implementation Reference (What Was Actually Built)

> Read this section before touching any Phase 4 code.

### 28.1 New Backend Files

```
backend/
├── alembic/versions/002_phase4.py       # OrgIntegration + GraphEdge tables
├── app/
│   ├── models/
│   │   ├── org_integration.py           # OrgIntegration SQLAlchemy model (Fernet-encrypted config)
│   │   └── graph_edge.py                # GraphEdge model (manual edges only; auto edges from graph_service)
│   ├── plugins/
│   │   ├── base.py                      # BasePlugin ABC + config_schema interface
│   │   ├── registry.py                  # @register_plugin decorator + plugin registry dict
│   │   ├── virustotal.py                # VirusTotal TI plugin (is_premium=False for basic)
│   │   ├── abuseipdb.py                 # AbuseIPDB TI plugin
│   │   ├── shodan.py                    # Shodan TI plugin (premium)
│   │   ├── microsoft_sentinel.py        # Sentinel SIEM plugin (premium)
│   │   ├── crowdstrike.py               # CrowdStrike EDR plugin (premium)
│   │   ├── microsoft_teams.py           # Teams comms plugin (premium)
│   │   ├── slack.py                     # Slack comms plugin (premium)
│   │   ├── jira.py                      # Jira ticketing plugin (premium)
│   │   ├── sharepoint.py                # SharePoint sync plugin (premium)
│   │   └── pagerduty.py                 # PagerDuty alerting plugin (premium)
│   ├── services/
│   │   ├── integration_service.py       # CRUD for org_integrations; Fernet encrypt/decrypt on config
│   │   ├── enrichment_service.py        # Multi-provider IOC enrichment; merges results into ioc.enrichment JSONB
│   │   └── graph_service.py             # Build GraphData (nodes + edges); networkx hierarchical layout
│   └── api/v1/
│       ├── integrations.py              # GET/POST/PATCH/DELETE /integrations + test endpoint
│       └── graph.py                     # GET /incidents/{id}/graph
```

### 28.2 Key Backend Patterns

**Plugin system:**
Each plugin file uses `@register_plugin` decorator. Plugin metadata (`name`, `category`, `is_premium`, `config_schema`) is defined as class attributes. `config_schema` is a dict that the frontend renders dynamically as a form. Adding a new integration = new plugin file only — no core code changes.

**Enrichment merge:**
`enrichment_service.enrich_ioc(ioc_id)` calls all enabled TI plugins in parallel (asyncio.gather). Results are merged under provider-keyed keys in `ioc.enrichment JSONB` (e.g., `enrichment["virustotal"]`, `enrichment["abuseipdb"]`). Frontend displays per-provider summaries in the IOC table enrichment column.

**Graph construction:**
`graph_service.build_graph(incident_id)` fetches all IOCs, timeline entries, and attachments. Nodes are created for each entity type. Edges are inferred (IOC → timeline_entry via `ioc_timeline_links`, timeline → attachment, etc.) plus loaded from `graph_edges` table (manual edges). networkx computes `spring_layout` positions which are returned as `x, y` on each node. Frontend receives `{ nodes: [...], edges: [...] }` ready for React Flow.

**Manual edges:**
`POST /api/v1/incidents/{id}/graph/edges` creates a `GraphEdge` row. `DELETE /api/v1/incidents/{id}/graph/edges/{edge_id}` removes it. Only manual edges (prefixed `manual-` in ID) can be deleted from the frontend.

**SharePoint Celery task:**
`sync_to_sharepoint(incident_id, policy_id)` in `tasks.py`: loads the SyncPolicy, decrypts `destination_config`, calls the SharePoint plugin's `sync()` method (renders the linked report template, uploads to the configured SharePoint document library), updates `last_synced_at` + `last_sync_status`, publishes `sync:complete` to Redis pub/sub.

### 28.3 New Frontend Files

```
frontend/src/
├── types/
│   ├── integration.ts                   # OrgIntegration, PluginMeta types
│   └── graph.ts                         # GraphNode, GraphEdge, GraphData, GraphNodeData types
├── hooks/
│   ├── useIntegrations.ts               # useIntegrations, useUpdateIntegration, useTestIntegration
│   └── useGraph.ts                      # useGraph, useAddGraphEdge, useDeleteGraphEdge
├── components/
│   ├── integrations/
│   │   └── IntegrationsPage.tsx         # Full implementation: plugin cards grouped by category,
│   │                                    # inline config forms, enable/disable toggle, enrichment display
│   └── graph/
│       ├── InvestigationGraph.tsx       # React Flow canvas: nodes/edges, toolbar, NodeDetailPanel
│       └── NodeTypes.tsx                # Custom React Flow node renderers per entity type
```

### 28.4 React Flow Integration Notes

- Package: `@xyflow/react` ^12.0.0 (added to `frontend/package.json`)
- `InvestigationGraph` is **lazy-loaded** from `IncidentWorkspacePage` via `React.lazy()` + `<Suspense>` — keeps initial bundle size under target
- Node types: `ioc`, `event`, `evidence`, `user`, `host`, `alert` — each has a custom renderer in `NodeTypes.tsx`
- Edge double-click → delete (manual edges only)
- Node click → `NodeDetailPanel` side panel with enrichment summary, IOC type, status, confidence
- `colorMode="dark"` passed to ReactFlow — adjusts built-in controls for dark theme
- Graph section tab added to `TopBar.tsx` SECTIONS array and rendered in `IncidentWorkspacePage.tsx`

### 28.5 Phase 4 Checklist (All Complete)

**Backend:**
- [x] Alembic migration 002 — `org_integrations` + `graph_edges` tables
- [x] OrgIntegration + GraphEdge SQLAlchemy models
- [x] Plugin infrastructure (base.py, registry.py)
- [x] 10 integration plugins (VT, AbuseIPDB, Shodan, Sentinel, CrowdStrike, Teams, Slack, Jira, SharePoint, PagerDuty)
- [x] `integration_service.py` — CRUD + Fernet encrypt/decrypt
- [x] `enrichment_service.py` — multi-provider parallel enrichment
- [x] `graph_service.py` — node/edge builder + networkx layout
- [x] `app/api/v1/integrations.py` — full CRUD + test endpoint
- [x] `app/api/v1/graph.py` — graph data + manual edge CRUD
- [x] `workers/tasks.py` — `enrich_ioc` (live) + `sync_to_sharepoint` (live)
- [x] `app/main.py` — integrations + graph routers registered

**Frontend:**
- [x] `src/types/integration.ts` + `src/types/graph.ts`
- [x] `src/hooks/useIntegrations.ts` + `src/hooks/useGraph.ts`
- [x] `src/components/integrations/IntegrationsPage.tsx` — full implementation (replaces Phase 2 shell)
- [x] `src/components/graph/InvestigationGraph.tsx` — React Flow canvas
- [x] `src/components/graph/NodeTypes.tsx` — custom node renderers
- [x] `frontend/package.json` — `@xyflow/react` added
- [x] `src/components/layout/TopBar.tsx` — Graph tab added to SECTIONS
- [x] `src/pages/IncidentWorkspacePage.tsx` — graph section rendered (lazy-loaded)

---

## 29. Phase 5 — Implementation Reference (What Was Actually Built)

> Read this section before touching any Phase 5 code.

### 29.1 New Backend Files

```
backend/
├── alembic/versions/003_phase5_enterprise.py  # user_invites + sso_configs tables + RLS on 6 tables
├── app/
│   ├── models/
│   │   ├── user_invite.py          # UserInvite ORM model
│   │   └── sso_config.py           # SSOConfig ORM model (SAML fields, role_mappings JSONB)
│   ├── schemas/
│   │   └── admin.py                # UserOut, InviteCreate/Out/Accept, OrgSettingsUpdate,
│   │                               # StorageConfigOut/Create, SSOConfigOut/Update, AuditLogOut
│   ├── services/
│   │   ├── email_service.py        # send_email() — console + SMTP (aiosmtplib) backends
│   │   │                           # send_invite_email() builds invite HTML
│   │   ├── audit_service.py        # log(), get_audit_log() (8 filter dims), export_csv()
│   │   ├── invite_service.py       # create, get_by_token, accept, list, revoke
│   │   ├── sso_service.py          # get/upsert config, get_saml_settings() → python3-saml dict
│   │   └── storage/
│   │       ├── s3.py               # S3StorageBackend (boto3, run_in_executor, presigned URLs)
│   │       ├── azure_blob.py       # AzureBlobStorageBackend (azure-storage-blob, SAS URLs)
│   │       ├── gcs.py              # GCSStorageBackend (google-cloud-storage, v4 signed URLs)
│   │       └── resolver.py         # Updated: get_storage_backend_from_config() for DB-driven backend
│   └── api/v1/
│       ├── users.py                # 8 routes: list, role change, deactivate, invite flow (public accept)
│       ├── audit.py                # GET /audit-log (paginated) + GET /audit-log/export (CSV)
│       ├── admin.py                # org settings, storage config CRUD+test+switch, SSO config CRUD
│       └── saml.py                 # GET /auth/saml/metadata, GET /auth/saml/login, POST /auth/saml/acs
```

### 29.2 Key Backend Patterns

**User invite flow:**
`POST /users/invite` creates a `UserInvite` row with `secrets.token_urlsafe(32)` token, 48h expiry, and fires `email_service.send_invite_email()`. `GET /users/invite/{token}` is public — returns 410 if expired or already accepted. `POST /users/invite/{token}/accept` creates the User (argon2id hashed password), marks `accepted_at`, then issues JWT + sets refresh cookie identical to normal login. Audit log entries written for `user.invited` and `user.created`.

**Last-admin guard:**
`PUT /users/{id}/role` and `PUT /users/{id}/deactivate` both count current admins first. If the action would leave the org with zero admins, they return HTTP 409 with a clear message.

**Audit service:**
All service-layer mutations call `await audit_service.log(db, ...)`. The `log()` function calls `db.flush()` but NOT `db.commit()` — the calling route's DB session owns the transaction, so audit writes are atomic with the main write. If the main write rolls back, so does the audit entry.

**RLS (Row-Level Security):**
Migration 003 enables RLS on `incidents`, `timeline_entries`, `iocs`, `attachments`, `tasks`, `reports`. A middleware sets `SET LOCAL app.current_org_id = '<uuid>'` at the start of every authenticated request. This is a DB-level guarantee — even a bug in application code cannot leak cross-org data.

**Cloud storage backends:**
All three backends wrap their SDKs' sync calls in `asyncio.get_event_loop().run_in_executor(None, ...)`. `get_url()` returns pre-signed/SAS URLs from the provider — never proxied through the API. `resolver.get_storage_backend_from_config(config_row)` instantiates the correct class from an already-decrypted `StorageConfig` DB row.

**Storage switch:**
`POST /admin/storage/switch` Fernet-encrypts the config dict, saves/updates the `storage_configs` row, then calls `get_storage_backend.cache_clear()` to flush the lru_cache. Subsequent requests use the new backend. Note: existing file URLs remain valid — they were issued by the old backend and point directly to that provider.

**SSO/SAML:**
`sso_service.get_saml_settings()` builds the python3-saml settings dict from the stored `SSOConfig`. `POST /auth/saml/acs` validates the SAML response, extracts email + name + groups, maps IdP groups to IRDoc roles via `sso_config.role_mappings`, creates or updates the user, then issues JWT + refresh cookie and redirects to `BASE_URL`. All python3-saml operations are wrapped in try/except — no library internals ever leak in API responses.

**New settings added to `config.py`:**
`SMTP_HOST/PORT/USER/PASSWORD/TLS`, `EMAIL_FROM`, `MSSP_MODE`.

**New packages in `requirements.txt`:**
`boto3`, `azure-storage-blob`, `google-cloud-storage`, `aiosmtplib`.

### 29.3 New Frontend Files

```
frontend/src/
├── types/admin.ts                   # OrgUser, UserInvite, OrgSettings, StorageConfigOut,
│                                    # SSOConfig, AuditLogEntry, ROLE_LABELS, ROLE_COLORS
├── hooks/useAdmin.ts                # All admin hooks: team, invites, org, storage, SSO, audit
├── lib/permissions.ts               # hasPermission(), usePermission() — role-hierarchy helpers
├── pages/
│   ├── InviteAcceptPage.tsx         # /invite/:token — validates, shows join form, auto-login on accept
│   └── AdminPage.tsx                # /admin — redirects non-admins, mounts AdminShell + tab pages
└── components/admin/
    ├── AdminShell.tsx               # Two-panel layout: sidebar nav (6 tabs) + content area
    ├── TeamPage.tsx                 # Active members table + pending invites + InviteModal
    ├── OrgSettingsPage.tsx          # Org name, plan, registration policy, custom branding (PremiumGate)
    ├── StoragePage.tsx              # 4 backend cards (S3/Azure/GCS in PremiumGate), test + switch
    ├── IncidentTemplatesPage.tsx    # System (clone only) + org templates + TemplateEditorPanel (dnd-kit)
    ├── AuditLogPage.tsx             # Filter bar, paginated table, high-risk badge, CSV export (PremiumGate)
    └── SSOPage.tsx                  # IdP selector, metadata loader, attr mapping, role mappings (PremiumGate)
```

### 29.4 Route Changes

New routes added to `App.tsx`:
- `/admin` → `AdminPage` (lazy-loaded, admin role redirect enforced in page)
- `/invite/:token` → `InviteAcceptPage` (lazy-loaded, **no auth required**)

### 29.5 LeftNav + LoginPage Changes

- `LeftNav.tsx`: Admin nav item (🛡️) added — visible only when `user.role === 'admin'`
- `LoginPage.tsx`: "Sign in with SSO" button added below the login form; calls `GET /auth/saml/login` and redirects to the returned `redirect_url`

### 29.6 Phase 5 Checklist (All Complete)

**Backend:**
- [x] Alembic migration 003 — `user_invites` + `sso_configs` + RLS on 6 tables
- [x] `models/user_invite.py` + `models/sso_config.py`
- [x] `schemas/admin.py` — all Phase 5 request/response schemas
- [x] `services/email_service.py` — console + SMTP backends
- [x] `services/audit_service.py` — write + paginated read + CSV export
- [x] `services/invite_service.py` — full invite lifecycle
- [x] `services/sso_service.py` — SAML config management
- [x] `services/storage/s3.py` — S3/MinIO/R2/Wasabi backend
- [x] `services/storage/azure_blob.py` — Azure Blob backend
- [x] `services/storage/gcs.py` — GCS backend
- [x] `services/storage/resolver.py` — updated with `get_storage_backend_from_config()`
- [x] `core/config.py` — SMTP settings + MSSP_MODE added
- [x] `requirements.txt` — boto3, azure-storage-blob, google-cloud-storage, aiosmtplib
- [x] `api/v1/users.py` — 8 routes incl. public invite accept
- [x] `api/v1/audit.py` — paginated log + CSV export
- [x] `api/v1/admin.py` — org settings + storage config + SSO config
- [x] `api/v1/saml.py` — metadata + login + ACS endpoints
- [x] `app/main.py` — users + audit + admin + saml routers registered

**Frontend:**
- [x] `src/types/admin.ts`
- [x] `src/hooks/useAdmin.ts`
- [x] `src/lib/permissions.ts`
- [x] `src/pages/InviteAcceptPage.tsx`
- [x] `src/pages/AdminPage.tsx`
- [x] `src/components/admin/AdminShell.tsx`
- [x] `src/components/admin/TeamPage.tsx`
- [x] `src/components/admin/OrgSettingsPage.tsx`
- [x] `src/components/admin/StoragePage.tsx`
- [x] `src/components/admin/IncidentTemplatesPage.tsx`
- [x] `src/components/admin/AuditLogPage.tsx`
- [x] `src/components/admin/SSOPage.tsx`
- [x] `src/App.tsx` — /admin + /invite/:token routes added
- [x] `src/components/layout/LeftNav.tsx` — Admin nav item (admin-only)
- [x] `src/pages/LoginPage.tsx` — SSO button added
---

## 30. Phase 6 — Implementation Reference (What Was Actually Built)

> Read this section before touching any Phase 6 (hardening/launch) files.

### 30.1 Files Created / Modified

```
incident-response-platform/
├── README.md                           # Full project README with quickstart, architecture, webhook guide
├── CHANGELOG.md                        # v1.0.0 changelog (Keep a Changelog format)
├── backend/
│   └── app/__init__.py                 # __version__ = "1.0.0"
├── docker/
│   ├── nginx/nginx.conf                # Updated: HSTS, blob: in img-src, wss: in connect-src, Permissions-Policy
│   ├── docker-compose.prod.yml         # Production compose — pre-built Hub images, worker+beat, SSL volume
│   ├── upgrade.sh                      # 4-step upgrade script (pull → migrate → restart → verify)
│   └── backup.sh                       # DB + local storage backup with 30-day rotation
├── .github/
│   └── workflows/
│       └── ci.yml                      # Full CI/CD: lint → pip-audit → pytest → npm audit → tsc → build → push
└── docs/
    ├── index.md                        # Docs site index + navigation
    ├── changelog.md                    # Pointer to root CHANGELOG.md
    ├── installation/
    │   ├── docker-compose.md           # Dev + production deployment guide, TLS setup
    │   ├── environment-variables.md    # All .env variables with descriptions
    │   ├── upgrading.md                # One-command upgrade + manual steps + rollback
    │   └── backup-restore.md           # Backup script, manual backup, restore, SHA-256 verify
    ├── user-guide/
    │   ├── timeline.md                 # Entry types, attachments, paste screenshots, filters, keyboard shortcuts
    │   ├── ioc-management.md           # IOC types, bulk import, status, confidence, TLP, enrichment
    │   ├── report-template-builder.md  # Block types, drag-and-drop canvas, preview
    │   ├── generating-reports.md       # Quick generate, downloading, formats, SharePoint sync
    │   ├── sharepoint-sync.md          # How it works, setup, debounce, troubleshooting
    │   └── keyboard-shortcuts.md       # N, Escape, Ctrl+Enter
    ├── admin-guide/
    │   ├── user-management.md          # Roles, invite flow, role change, deactivate, last-admin guard
    │   ├── storage-backends.md         # Local, S3, Azure Blob, GCS — setup + switching
    │   ├── api-keys.md                 # Create, scopes, SDP/Jira webhook setup guide
    │   ├── sso-saml.md                 # Okta/Azure/Google setup, role mappings, auto-provision
    │   └── integrations/
    │       └── servicedesk-plus.md     # SDP notification rule + webhook body + troubleshooting
    ├── api/
    │   └── reference.md               # Links to /api/docs, auth methods, envelope, key endpoints, rate limits
    └── contributing/
        ├── development-setup.md        # Python + Node + Docker local dev walkthrough
        ├── architecture.md             # System diagram, key design principles, auth flow, real-time
        └── adding-integrations.md      # Plugin system tutorial with full example + config schema types
```

### 30.2 Nginx Security Headers (Updated)

The full header suite now includes:
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` (HSTS)
- `Content-Security-Policy` — `img-src` includes `blob:` (needed for React Flow canvas export); `connect-src` uses `wss:` (WebSocket)
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- Removed `X-XSS-Protection` (deprecated, removed from spec)

### 30.3 CI/CD Pipeline Key Decisions

- `pip-audit` runs against `requirements.txt` directly (no virtual env install needed in CI)
- Secret leak check: `grep -rn "irp_key_\|sk-ant-\|AKIA\|sk-proj-"` — fails the job if any hit
- Bundle size check is a **warning** not a failure (prints size, warns if over 200KB)
- Multi-arch build uses `docker/setup-qemu-action` for arm64 cross-compilation
- Release job only runs on GitHub Release creation (not on every tag push)
- Codecov integration for backend coverage reporting

### 30.4 Production Compose Differences from Dev Compose

| Feature | Dev (`docker-compose.yml`) | Prod (`docker-compose.prod.yml`) |
|---|---|---|
| Images | Built from source | Pre-built from Docker Hub |
| Backend port | `8000:8000` exposed | `expose: 8000` (internal only) |
| SSL | Not configured | `./ssl:/etc/nginx/ssl:ro` volume |
| HTTP/HTTPS ports | Configurable via `HTTP_PORT`/`HTTPS_PORT` env vars | |
| Redis persistence | No save | `--save 60 1` + `--appendonly yes` |
| Worker concurrency | Default | `-c 4` explicit |
| `ALLOW_REGISTRATION` | `true` | `false` (require invites) |

### 30.5 Phase 6 Checklist (All Complete)

- [x] `nginx.conf` — full security header suite (HSTS, CSP with blob/wss, Permissions-Policy)
- [x] `backend/app/__init__.py` — `__version__ = "1.0.0"`
- [x] `docker/docker-compose.prod.yml` — production compose with pre-built Hub images
- [x] `docker/upgrade.sh` — 4-step upgrade with version verification
- [x] `docker/backup.sh` — DB + storage backup with 30-day rotation
- [x] `.github/workflows/ci.yml` — full CI/CD pipeline (lint, audit, test, build, push, release)
- [x] `README.md` — complete with quickstart, features, architecture, webhook guide, contributing
- [x] `CHANGELOG.md` — v1.0.0 in Keep a Changelog format
- [x] `docs/` — 18 documentation files covering installation, user guide, admin guide, API, contributing

---

## 31. Assets Feature — Implementation Reference (Post-Launch Addition)

> Read this section before touching any Assets-related code.

### 31.1 New Files

```
backend/
├── alembic/versions/004_assets.py       # assets, asset_timeline_links, asset_links tables
├── app/
│   ├── models/asset.py                  # Asset, AssetTimelineLink, AssetLink ORM models
│   ├── schemas/asset.py                 # AssetCreate, AssetBulkCreate, AssetUpdate, AssetOut,
│   │                                    # AssetLinkCreate, AssetLinkOut, AssetTimelineLinkCreate
│   ├── services/asset_service.py        # CRUD, bulk create, timeline linking, asset-link CRUD
│   └── api/v1/assets.py                 # 9 REST endpoints

frontend/src/
├── types/asset.ts                       # Asset, AssetLink types + ASSET_TYPE_ICONS/LABELS/COLORS,
│                                        # ASSET_LINK_TYPE_LABELS, ASSET_TYPES_LIST, ASSET_LINK_TYPES_LIST
├── hooks/useAssets.ts                   # useAssets, useBulkCreateAssets, useCreateAsset,
│                                        # useUpdateAsset, useDeleteAsset, useAssetLinks,
│                                        # useCreateAssetLink, useDeleteAssetLink,
│                                        # useLinkAssetsToEntry, useEntryAssets
└── components/assets/AssetsPage.tsx     # Main page: List sub-tab + Relationships sub-tab
```

### 31.2 Modified Files

- `backend/app/models/__init__.py` — added Asset, AssetTimelineLink, AssetLink imports
- `backend/app/models/timeline.py` — added `asset_links` relationship to `TimelineEntry`
- `backend/app/core/permissions.py` — added `assets.read/create/update/delete` permissions
- `backend/app/main.py` — registered assets router (Phase 4 block)
- `backend/app/services/graph_service.py` — asset nodes + asset-link edges + asset-timeline-entry edges
- `frontend/src/types/graph.ts` — NodeType union extended with 16 asset types; `ASSET_STATUS_COLORS` added
- `frontend/src/components/graph/NodeTypes.tsx` — 16 AssetNode renderers; `NODE_TYPES` map extended
- `frontend/src/components/layout/TopBar.tsx` — Assets tab added between IOCs and Summary
- `frontend/src/pages/IncidentWorkspacePage.tsx` — `Section` type includes `'assets'`; `AssetsPage` rendered
- `frontend/src/components/timeline/AddEntryForm.tsx` — collapsible asset picker (links assets on submit)
- `frontend/src/components/layout/LeftNav.tsx` — default expanded (210px), collapsible to 60px with `‹/›` toggle, `nav-collapsed` localStorage key

### 31.3 Database Tables

**`assets`** — id, incident_id (FK → incidents, CASCADE), asset_type VARCHAR(30), name TEXT, description TEXT, status VARCHAR(20) default "suspected", criticality VARCHAR(20) default "medium", tags TEXT[], metadata JSONB, added_by (FK → users, SET NULL), created_at, updated_at

**`asset_timeline_links`** — asset_id (FK → assets, CASCADE) + timeline_entry_id (FK → timeline_entries, CASCADE), composite PK

**`asset_links`** — id, incident_id (FK → incidents, CASCADE), source_id (FK → assets, CASCADE), target_id (FK → assets, CASCADE), link_type VARCHAR(40), label TEXT, created_by (FK → users, SET NULL), created_at
- CHECK: source_id != target_id
- UNIQUE: (source_id, target_id, link_type)

Indexes: `ix_assets_incident_id`, `ix_assets_incident_type`, `ix_assets_status`, `ix_asset_timeline_links_entry`, `ix_asset_links_incident`, `ix_asset_links_source`, `ix_asset_links_target`

### 31.4 Asset Types (16)

`host`, `server`, `workstation`, `laptop`, `mobile`, `network_device`, `account`, `service_account`, `file`, `directory`, `url`, `email_address`, `database`, `application`, `cloud_resource`, `other`

### 31.5 Asset Link Types (10)

`communicates_with`, `owns`, `runs`, `connects_to`, `authenticates_to`, `contains`, `accesses`, `lateral_movement`, `exfiltration_target`, `related`

### 31.6 Asset Statuses and Criticalities

Statuses: `suspected` (default) → `confirmed` → `remediated` → `cleared`
Criticalities: `critical`, `high`, `medium` (default), `low`

### 31.7 API Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/incidents/{id}/assets` | assets.read | List all assets |
| POST | `/incidents/{id}/assets` | assets.create | Create single asset |
| POST | `/incidents/{id}/assets/bulk` | assets.create | Bulk create (one name per line) |
| PUT | `/incidents/{id}/assets/{asset_id}` | assets.update | Update asset |
| DELETE | `/incidents/{id}/assets/{asset_id}` | assets.delete | Delete asset |
| POST | `/incidents/{id}/assets/timeline-links` | assets.create | Link assets to timeline entry |
| DELETE | `/incidents/{id}/assets/{asset_id}/timeline-links/{entry_id}` | assets.create | Unlink |
| GET | `/incidents/{id}/timeline/{entry_id}/assets` | assets.read | List assets for entry |
| GET | `/incidents/{id}/asset-links` | assets.read | List asset-to-asset relationships |
| POST | `/incidents/{id}/asset-links` | assets.create | Create relationship |
| DELETE | `/incidents/{id}/asset-links/{link_id}` | assets.delete | Delete relationship |

### 31.8 Key Patterns

**`metadata_` alias:** Same as `Incident` and `TimelineEntry` — ORM attribute is `metadata_`, column is `"metadata"`. `AssetOut.model_validate()` copies `metadata_` → `metadata` before serialization.

**Bulk create:** `POST /assets/bulk` accepts `{ asset_type, names: string[], ... }` — server loops and creates one `Asset` row per name (stripping whitespace, skipping blanks).

**Graph integration:** `graph_service.build_graph()` now adds:
1. One node per asset (`id: "asset-{uuid}"`, `type: "asset_{asset_type}"`)
2. Edges from `asset_links` table (`source → target`, label = custom label or link_type)
3. Edges from `asset_timeline_links` (asset → timeline entry node, only if entry node is in graph)

**Asset picker in AddEntryForm:** Only shown when the incident has ≥1 asset. Collapsed by default. On submit, calls `POST /assets/timeline-links` with all selected asset IDs and the new entry ID.

### 31.9 Assets Feature Checklist (All Complete)

- [x] Alembic migration 004 — `assets`, `asset_timeline_links`, `asset_links`
- [x] ORM models: `Asset`, `AssetTimelineLink`, `AssetLink`
- [x] Pydantic schemas: `AssetCreate`, `AssetBulkCreate`, `AssetUpdate`, `AssetOut`, `AssetLinkCreate`, `AssetLinkOut`, `AssetTimelineLinkCreate`
- [x] `asset_service.py` — full CRUD + bulk + timeline links + asset-link CRUD
- [x] RBAC: `assets.read/create/update/delete` permissions (viewer/analyst/analyst/senior_analyst)
- [x] REST router `api/v1/assets.py` — 11 endpoints registered
- [x] `graph_service.py` — asset nodes + 2 edge types (asset→asset, asset→timeline entry)
- [x] `frontend/src/types/asset.ts` — all types + display constants
- [x] `frontend/src/types/graph.ts` — NodeType union + `ASSET_STATUS_COLORS`
- [x] `frontend/src/hooks/useAssets.ts` — full hook suite
- [x] `frontend/src/components/assets/AssetsPage.tsx` — List + Relationships sub-tabs
- [x] `frontend/src/components/graph/NodeTypes.tsx` — 16 asset node renderers
- [x] `TopBar.tsx` — Assets tab (between IOCs and Summary)
- [x] `IncidentWorkspacePage.tsx` — `assets` section renders `AssetsPage`
- [x] `AddEntryForm.tsx` — collapsible asset picker, links on submit
- [x] `LeftNav.tsx` — expanded by default, `‹/›` collapse toggle, localStorage persistence

---

## 32. Post-Launch UI Fixes (Batch 1)

### 32.1 Integrations Moved to Admin Panel *(superseded by 32.6)*

**Problem:** Integrations was a standalone left-nav item, disconnected from the Admin area.

**Changes (original):** Moved integrations into `AdminShell` sidebar. Superseded by 32.6 which removes `AdminShell` entirely.

### 32.2 Incident Section Persists on Refresh

**Problem:** Refreshing an open incident page reset to the incident list, and the active section was always `timeline` regardless of URL.

**Fix:** `IncidentWorkspacePage.tsx` — `activeSection` state initialized from `useParams<{ id; section? }>()`. `VALID_SECTIONS` array used to validate and fall back to `'timeline'`. The `/incidents/:id/:section` route already existed in `App.tsx`.

### 32.3 Summary Tab Stat Cards Simplified

**Problem:** Summary tab had 6 stat cards (Severity, Status, Timeline, IOCs, Tasks, Affected Users) — data that is already visible elsewhere, adding clutter.

**Fix:** `SummaryPage.tsx` — removed `useIncidentStats` import and hook call; removed Timeline, IOCs, Tasks, and Affected Users stat cards. Kept Severity and Status cards only.

### 32.4 IOC Confidence UI Redesigned

**Problem:** Confidence was a tiny 60px number input labeled `Conf:` — not discoverable or readable.

**Fix:** `IOCPage.tsx` — restructured add form into two rows:
- Row 1: type selector + IOC value input
- Row 2: labeled `Confidence (0–100)` with a range slider (0–100, step 5) + color-coded percentage display (green ≥70, yellow ≥40, red <40)

### 32.5 Evidence Timeline Dot Opacity Fixed

**Problem:** `evidence` entry type dot used `var(--purple-dim)` (~12% opacity) — the vertical timeline line was visible through it.

**Fix:** `TimelineEntry.tsx` — changed `evidence` bg in `DOT_STYLES` from `var(--purple-dim)` to `rgba(188,140,255,0.45)` (~45% opacity), solid enough to cover the line.

### 32.6 Admin Panel Flattened into Main Nav (Management Section)

**Problem:** Admin features were buried two levels deep (LeftNav → Admin → AdminShell sidebar). Users had to navigate away from the main app shell to access any admin function.

**Fix:** Removed the separate `AdminShell`-based admin panel. All admin items are now first-class entries in `LeftNav` under a "MANAGEMENT" section separator, visible only to admin-role users.

**Changes:**
- `LeftNav.tsx` — added `MANAGEMENT_ITEMS` array (8 items: Team, Org Settings, Storage, Incident Templates, Report Templates, Integrations, Audit Log, SSO). Renders a "MANAGEMENT" label separator (collapsed: horizontal rule only) above these items. Removed standalone "Admin" nav button.
- `AdminPage.tsx` — rewritten: uses `useParams<{ section? }>()` instead of `useState` for active tab. Wraps in `AppShell` instead of `AdminShell`. Section defaults to `'team'` if missing/invalid. Retains admin role guard (redirects non-admins).
- `App.tsx` — `/admin` now redirects to `/admin/team`. Old `/admin` route replaced with `/admin/:section`. `/integrations` redirect updated to `/admin/integrations`.
- `AdminShell.tsx` — no longer used (kept in codebase, not rendered).

**Routes:**
```
/admin              → redirect → /admin/team
/admin/team         → AdminPage (section=team)
/admin/org          → AdminPage (section=org)
/admin/storage      → AdminPage (section=storage)
/admin/templates    → AdminPage (section=templates)
/admin/reports      → AdminPage (section=reports)
/admin/integrations → AdminPage (section=integrations)
/admin/audit        → AdminPage (section=audit)
/admin/sso          → AdminPage (section=sso)
```

---

## 33. Reports Simplification (v1.0 DOCX Template Flow)

### 33.1 Overview

The block-based report template system (Management Brief, Technical Report, Legal) is preserved intact for v2.0. For v1.0 we implement a simpler DOCX template workflow:

1. User downloads a base `.docx` scaffold from Admin → Report Templates
2. User edits it in Word (adds company logo, adjusts styles) — **must not remove `{{PLACEHOLDER}}` markers**
3. User uploads their customised `.docx` back to IRDoc
4. Any uploaded template can be set as the org default
5. From Incident → Reports tab, user picks a template card and clicks "Generate DOCX"

### 33.2 Backend (All New)

**Model:** `backend/app/models/docx_template.py` — `DocxTemplate` table (`docx_templates`)
- Fields: `id`, `org_id` (FK, indexed), `name`, `is_default`, `storage_path`, `file_size`, `created_by`, `created_at`, `updated_at`

**Migration:** `backend/alembic/versions/005_docx_templates.py` (`down_revision = "004"`)

**Schema:** `backend/app/schemas/docx_template.py` — `DocxTemplateOut`, `DocxTemplateRename`

**Service:** `backend/app/services/docx_template_service.py`
- `generate_base_template()` — generates a fully-structured DOCX with all `{{PLACEHOLDER}}` markers using python-docx
- `render_with_template(template_bytes, payload, classification)` — replaces placeholders (using run-merging to handle Word's run-splitting), inserts Word tables at `{{SECTION}}` markers
- Key placeholder set: `{{INCIDENT_TITLE}}`, `{{INCIDENT_REF}}`, `{{SEVERITY}}`, `{{STATUS}}`, `{{CREATED_AT}}`, `{{CONTAINED_AT}}`, `{{CLOSED_AT}}`, `{{DURATION}}`, `{{AFFECTED_USERS}}`, `{{ATTACK_VECTOR}}`, `{{EXECUTIVE_SUMMARY}}`, `{{TIMELINE_COUNT}}`, `{{IOC_COUNT}}`, `{{TASK_COMPLETION_PCT}}`, `{{TIMELINE_SECTION}}`, `{{IOC_TABLE}}`, `{{TASKS_TABLE}}`, `{{EVIDENCE_TABLE}}`, `{{GENERATED_AT}}`, `{{GENERATED_BY}}`, `{{CLASSIFICATION}}`
- Table marker insertion uses `para._element.addnext(table._tbl)` XML manipulation

**API:** `backend/app/api/v1/docx_templates.py`
- `GET /docx-templates` — list org templates
- `GET /docx-templates/base` — download base scaffold
- `POST /docx-templates` — upload (multipart: `name` + `file`)
- `PATCH /docx-templates/{id}` — rename
- `POST /docx-templates/{id}/set-default` — set as org default
- `DELETE /docx-templates/{id}` — delete

**report_service.py changes:** DOCX template path added — when `docx_template_id` is set or `format='docx'` without `report_template_id`, uses the new path. DOCX export no longer premium-gated for custom templates.

**tasks.py changes:** `generate_report` accepts optional `docx_template_id`. If present → `render_with_template`. If `format='docx'` with no template → use generated base template. Else → existing block-based `ReportRenderer`.

### 33.3 Frontend (All New/Modified)

**`frontend/src/types/report.ts`** — `ReportGenerateRequest.report_template_id` made optional; `docx_template_id?: string` added

**`frontend/src/types/docxTemplate.ts`** (new) — `DocxTemplate` interface

**`frontend/src/hooks/useDocxTemplates.ts`** (new) — `useDocxTemplates`, `useDownloadBaseTemplate`, `useUploadDocxTemplate`, `useSetDefaultDocxTemplate`, `useRenameDocxTemplate`, `useDeleteDocxTemplate`

**`frontend/src/components/admin/ReportsAdminPage.tsx`** (new) — Admin → Report Templates page
- Section 1: Download Base Template (info + button)
- Section 2: Upload Custom Template (name input + file picker)
- Section 3: Your Templates list (inline rename, set-default, delete; default gets accent border + DEFAULT chip)

**`frontend/src/components/reports/ReportPage.tsx`** (rewritten)
- Removed: block-template cards (Management Brief, Technical Report, Legal), GenerateReportModal, SyncPolicySection
- Added: "Generate a Report" grid — Base Template card (always shown) + custom template cards from `useDocxTemplates()`
- Each card has a "Generate DOCX" button that calls `generateReport.mutateAsync({ format: 'docx', docx_template_id, ... })`
- Generated Reports table retained as-is

**`frontend/src/components/admin/AdminShell.tsx`** — `AdminTab` type + `SIDEBAR_ITEMS` extended with `'reports'` (`📄 Report Templates`)

**`frontend/src/pages/AdminPage.tsx`** — imports `ReportsAdminPage`, renders for `activeTab === 'reports'`

### 33.4 DOCX Placeholder Run-Merging

Word splits paragraph text across multiple XML runs (formatting boundaries). To replace `{{FIELD}}`:
1. Concatenate all run texts in the paragraph
2. Apply all replacements to the concatenated string
3. Put result in `run[0].text`, clear `run[n].text` for n > 0

For table markers (`{{TIMELINE_SECTION}}` etc.):
1. Add table at end of doc body
2. Detach from body: `table._tbl.getparent().remove(table._tbl)`
3. Insert after marker: `para._element.addnext(table._tbl)`
4. Remove marker paragraph

---

## 34. Critical Bug Fixes (Post-Launch)

> Fixes for the 3 critical issues identified in the UX Research Bug Report (March 2026).

### 34.1 Bug Fix: Silent WebSocket Failures

**Files changed:** `frontend/src/lib/websocket.ts`, `frontend/src/stores/uiStore.ts`, `frontend/src/components/layout/AppShell.tsx`

**Problem:** Socket.io had no error or disconnect handlers. When the WebSocket connection dropped (404s seen in logs), real-time updates silently stopped with no user feedback.

**Fix:**
- Added `wsConnected: boolean` + `setWsConnected()` to `uiStore.ts`
- `websocket.ts` — `getSocket()` now registers `connect`, `disconnect`, `connect_error`, `reconnect`, `reconnect_failed` handlers that call `useUIStore.getState().setWsConnected()`
- `AppShell.tsx` — renders a yellow banner `"Real-time connection lost. Reconnecting… Live updates are paused."` whenever `wsConnected` is `false`
- `wsConnected` defaults to `true` (no false-negative flash on first load before the socket connects)

### 34.2 Bug Fix: Mid-Work Session Expiry with No Warning

**Files changed:** `frontend/src/lib/apiClient.ts`, `frontend/src/App.tsx`, `frontend/src/pages/LoginPage.tsx`

**Problem:** When the refresh token expired, the user was silently redirected to `/login` mid-work with no explanation and no opportunity to save.

**Fix:**
- `apiClient.ts` — added `scheduleTokenRefresh(token)` export:
  - Decodes `exp` from the JWT payload (`atob(token.split('.')[1])`) without a library
  - Sets a timer to fire a warning toast 2 min before expiry: _"Your session expires soon. Save your work…"_
  - Sets a timer to silently proactively refresh the token 1 min before expiry
- `apiClient.ts` 401 interceptor — calls `scheduleTokenRefresh(newToken)` after each successful refresh; redirects to `/login?reason=session_expired` on hard logout
- `App.tsx` — calls `scheduleTokenRefresh(token)` after session restore on page load
- `LoginPage.tsx` — reads `?reason=session_expired` via `useSearchParams` and pre-fills the error state with `"Your session expired. Please log in again."`

### 34.3 Bug Fix: Attachment Upload Failures Hidden by Premature Success Toast

**Files changed:** `frontend/src/components/timeline/AddEntryForm.tsx`

**Problem:** The "Entry added" success toast fired immediately after the timeline entry was created, before the file upload loop ran. If uploads failed, only per-file error toasts followed — users who glanced away missed them entirely.

**Fix:**
- Moved the result toast to after all uploads complete
- Track `uploadedCount` and `failedCount` across the upload loop (removed per-file individual error toasts)
- Toast logic:
  - No files queued → `"Entry added"` (unchanged)
  - All uploads succeeded → `"Entry added. N attachment(s) uploaded."` (success)
  - Some failed → `"Entry added. N of M attachment(s) uploaded — X failed."` (error — persists until dismissed)

---

## 35. Post-Launch UI Fixes (Batch 2)

### 35.1 Admin Panel Flattened into Main Nav

See Section 32.6 — all admin items now appear as first-class entries in `LeftNav` under a "MANAGEMENT" separator. `AdminShell` is no longer rendered.

### 35.2 Team Merged into Org Settings Page

**Problem:** "Team" was a separate nav item and separate page, but it belongs logically under Organisation settings alongside Registration Policy, Custom Branding, and User Authentication.

**Changes:**
- `OrgSettingsPage.tsx` — fully rewritten: absorbs all of `TeamPage`'s functionality (active members table, inline role edit, deactivate, pending invitations, resend/revoke) as a "Team Members" card block. Adds a new "User Authentication" block (see 35.3). All hooks imported inline; shared style constants extracted at file top.
- `LeftNav.tsx` — `MANAGEMENT_ITEMS` no longer includes `{ label: 'Team', path: '/admin/team' }`.
- `AdminPage.tsx` — `team` removed from `AdminSection` type and `VALID_SECTIONS`. `TeamPage` import removed. Legacy `/admin/team` URL redirected to `/admin/org` via a `useEffect`.
- `App.tsx` — `/admin` redirect changed from `/admin/team` → `/admin/org`. Unused `IntegrationsPageWrapper` import removed.

### 35.3 User Authentication Block (new)

Added to `OrgSettingsPage.tsx` as a card between "Team Members" and "Registration Policy".

Three radio-card options:
- **🔑 Local Users** (free, default) — shows a "Break-Glass Admin" sub-card (`local.admin` account, rotate-password button).
- **☁️ Entra ID / Azure AD** — when selected, shows a compact status chip + "Configure SSO →" button that navigates to `/admin/integrations?section=identity`.
- **🏢 On-Premises AD** — when selected, shows a compact status chip + "Configure SSO →" button that navigates to `/admin/integrations?section=identity`.

Inspired by the prototype at `incident-response-platform_new/js/view-org.js`.

### 35.5 SSO Moved into Integrations — Identity & Access Section

**Decision:** SSO is an external identity provider integration and belongs alongside VirusTotal, Slack, and SharePoint — not as a separate admin section. `IntegrationsPage` is now the single hub for all external service configuration.

**Changes:**
- `frontend/src/components/integrations/IntegrationsPage.tsx` — Added `IdentitySection` component with a full-width SSO / SAML 2.0 card. Card shows status + enable toggle; clicking "Configure ▼" expands an inline form with 4 sub-sections (Identity Provider, Attribute Mapping, Role Mappings, SP Metadata). Uses `useSSOConfig` / `useUpdateSSOConfig` hooks directly. Reads `?section=identity` query param on mount to auto-expand the card (used for deep-linking from Org Settings).
- `frontend/src/components/admin/OrgSettingsPage.tsx` — Entra ID and On-Premises AD sub-panels simplified to a compact status row + "Configure SSO →" button that navigates to `/admin/integrations?section=identity`. Removed unused `ldapServer` / `ldapBaseDn` state.
- `frontend/src/components/layout/LeftNav.tsx` — Removed `{ icon: '🔐', label: 'SSO', path: '/admin/sso' }` from `MANAGEMENT_ITEMS`.
- `frontend/src/pages/AdminPage.tsx` — Removed `'sso'` from `AdminSection` type and `VALID_SECTIONS`. Removed `SSOPage` import. Added legacy redirect: `section === 'sso'` → `/admin/integrations?section=identity`.
- `frontend/src/App.tsx` — Added `/admin/sso` route redirecting to `/admin/integrations?section=identity` for any bookmarked links.

**Navigation flow:**
```
Org Settings → User Auth → pick Entra ID → "Configure SSO →"
  → /admin/integrations?section=identity
  → IntegrationsPage mounts, reads ?section=identity, auto-expands SSO card
```

**Backend untouched** — `SSOPage.tsx` is no longer rendered but kept in codebase. All SAML backend logic (`/auth/saml/*` routes, `sso_service.py`, `SSOConfig` model) unchanged.

### 35.4 All Features Moved to CORE Plan

**Decision:** All premium-gated features are now available on the CORE plan. The backend premium infrastructure (`check_feature()`, `LICENSE_KEY`, feature flags endpoint, `organizations.plan` column) is preserved intact and ready to be reactivated if a licensing tier is introduced in the future.

**Changes:**
- `frontend/src/components/common/PremiumGate.tsx` — Rewritten as a transparent passthrough: `return <>{children}</>`. The `useFeatureFlags` hook import removed. Props interface (`feature`, `featureKey`, `children`) kept intact. The original lock overlay (blurred backdrop, 🔒 icon, "Premium Feature" label, "Upgrade to unlock →" link) is preserved in a comment block for future restoration.
- `frontend/src/components/admin/OrgSettingsPage.tsx` — Removed `isPremium` variable and all associated client-side gating from the User Authentication radio cards: removed `opacity: 0.6` dimming, removed `disabled` on radio inputs, removed cursor override to `'default'`, removed 🔒 lock icon. All three auth options (Local Users, Entra ID / Azure AD, On-Premises AD) are now fully selectable.
- **Backend untouched** — `app/core/feature_flags.py`, `check_feature()` calls in services and routes, and the `organizations.plan` column all remain as-is.

