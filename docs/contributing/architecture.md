# Architecture Overview

---

## System Diagram

```
┌────────────────────────────────────────────────────────────────┐
│  Browser                                                        │
│  React 18 + TypeScript (Vite, Zustand, TanStack Query)         │
└────────────────────────┬───────────────────────────────────────┘
                         │ HTTP + WebSocket
                         ▼
┌────────────────────────────────────────────────────────────────┐
│  Nginx                                                          │
│  Reverse proxy + static file serving                           │
│  Security headers (HSTS, CSP, X-Frame-Options, etc.)           │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────┐
│  FastAPI (Python 3.12, async)                                   │
│  ├─ API routes (thin — no business logic)                       │
│  ├─ Services (all business logic)                               │
│  ├─ Models (SQLAlchemy 2 ORM)                                   │
│  ├─ Schemas (Pydantic v2)                                       │
│  ├─ Plugins (integration registry)                              │
│  └─ Socket.io server (real-time collaboration)                  │
└──────┬──────────────────────────┬─────────────────────────────┘
       │                          │ Redis pub/sub
       ▼                          ▼
┌─────────────┐    ┌──────────────────────────────────────────────┐
│ PostgreSQL  │    │  Celery Workers                               │
│ 16          │    │  ├─ generate_report                           │
│ JSONB       │    │  ├─ enrich_ioc                                │
│ RLS         │    │  ├─ sync_to_sharepoint                        │
│ tsvector    │    │  ├─ auto_detect_iocs_from_entry               │
│             │    │  ├─ generate_ai_summary                       │
└─────────────┘    │  └─ verify_file_hash                          │
       ▲           └──────────────────────────────────────────────┘
       │                          │
       └──────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────┐
│  Redis 7                                                        │
│  ├─ Celery broker + result backend                              │
│  ├─ Pub/sub (report:ready, sync:complete → WebSocket)           │
│  ├─ SharePoint debounce TTL keys                                │
│  └─ Feature flag cache                                          │
└────────────────────────────────────────────────────────────────┘
```

---

## Key Design Principles

### Routes are thin
All business logic lives in `services/`. Routes validate input (via Pydantic), call a service function, and return a response. No business logic in route handlers.

### StorageBackend protocol
All file I/O goes through the `StorageBackend` protocol. This makes storage pluggable at runtime without code changes.

```python
class StorageBackend(Protocol):
    async def store(data: bytes, path: str) -> str: ...
    async def retrieve(path: str) -> bytes: ...
    async def delete(path: str) -> None: ...
    async def get_url(path: str, expires_in: int = 3600) -> str: ...
    async def test_connection() -> bool: ...
```

### Schema-driven reports
Reports are not hardcoded Jinja2 templates. Users compose report schemas (ordered block arrays stored as JSONB). The renderer iterates blocks and assembles partials. Adding a new block type = new Jinja2 partial + renderer entry, no DB migration.

### Plugin system
Each integration is a single decorated class. The `@register_plugin` decorator adds it to the global registry. The frontend dynamically renders `config_schema` as a form.

### Debounce pattern (SharePoint)
Any write sets a Redis TTL key. If another write arrives before TTL expires, the key TTL resets. When TTL expires, Redis keyspace notification fires → Celery task runs.

### Audit log atomicity
`audit_service.log()` calls `db.flush()` not `db.commit()`. The calling route owns the transaction. If the main write rolls back, so does the audit entry — no orphaned audit records.

### Row-level security
PostgreSQL RLS policies enforce org isolation at the database level. Even a bug in application code cannot leak cross-org data. Middleware sets `SET LOCAL app.current_org_id = '<uuid>'` per request.

---

## Directory Structure

```
backend/app/
├── api/v1/          # Thin route handlers (no business logic)
├── core/            # Config, security, RBAC, feature flags, debounce
├── models/          # SQLAlchemy 2 ORM models
├── schemas/         # Pydantic v2 request/response models
├── services/        # All business logic
│   ├── storage/     # StorageBackend implementations
│   └── report_renderer/  # Jinja2 engine + block renderers
├── plugins/         # Integration plugin system
└── workers/         # Celery tasks

frontend/src/
├── components/      # UI components (layout, timeline, ioc, reports, graph, admin)
├── pages/           # Top-level pages
├── hooks/           # TanStack Query hooks (server state)
├── stores/          # Zustand stores (UI state: auth, theme, toasts)
├── lib/             # apiClient, websocket, iocDetector, utils
├── types/           # TypeScript type definitions
└── styles/          # global.css (CSS variables, utility classes)
```

---

## Auth Flow

1. `POST /auth/login` → returns JWT access token (15 min) + sets HttpOnly refresh cookie (30 days)
2. Access token stored in Zustand memory only — never localStorage
3. On 401: Axios interceptor calls `POST /auth/refresh` → new access token → replay original request
4. On refresh failure: clear store, redirect to login
5. On app load: `App.tsx` calls `/auth/refresh` silently to restore session from cookie

---

## Real-Time Collaboration

1. Analyst opens incident workspace → frontend emits `join:incident` via Socket.io
2. Another analyst adds a timeline entry → backend broadcasts `timeline:entry:added`
3. All analysts in that room receive the event → TanStack Query invalidates `['timeline', id]` → UI re-fetches

Report generation completion and SharePoint sync use Redis pub/sub → Socket.io re-emit.
