# Changelog

All notable changes to IRDoc are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
IRDoc uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The current pre-release version is tracked in [`VERSION`](VERSION).

---

## [Unreleased]

### Fixed

- **Incident tabs and left-nav frozen after the first click** — `react-router-dom` v7's `<BrowserRouter>` now wraps every location update in `React.startTransition()` by default. Under React 18, that transition-wrapped update to `<Routes>` could be starved by other synchronous re-renders in the tree (zustand/WebSocket-driven state on the incident workspace page) and never commit, even though `history.pushState`/`replaceState` had already changed the URL — so a tab or nav click changed the address bar but left the previous screen on-screen, and every navigation afterwards (any tab, any nav item) stayed stuck until a full page reload. Fixed by opting out with `useTransitions={false}`, restoring synchronous route updates.
- **`beat` container always reporting unhealthy** — its healthcheck shells out to `pgrep`, which isn't part of the `python:3.12-slim-bookworm` base image (no `procps`); it has failed with `pgrep: not found` (exit 127) every 30s since the healthcheck was added, even though the `celery beat` process itself was running fine. Added `procps` to `backend/Dockerfile`.

## [0.1.1-alpha] - 2026-09-18

### Fixed

- **Fresh Docker installs crash-looping on first run** — `docker-compose.prod.yml` set `AI_BACKEND` to an always-injected empty string by default; the backend's `Literal["anthropic","openai","ollama"]` setting rejects that at startup, crash-looping `backend`, `worker`, and `beat` together (they share one entrypoint that imports settings before starting anything). `AI_BACKEND` now defaults to `anthropic`, matching the app's own default.
- **First-run setup screen not appearing** — `GET /auth/setup-status` returned a bare `{"setup_complete": ...}` instead of the `{"data": {...}}` envelope every other endpoint uses. The frontend's response parsing threw against the unexpected shape and failed silently, so a fresh install with zero users rendered a normal login form with no way to create the first admin account.
- `docker-compose.prod.yml` now passes `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, and `OLLAMA_BASE_URL` through to the backend — setting these in `docker/.env` had no effect before this release.
- Removed the misleading `EMAIL_BACKEND` line from `.env.example`; it isn't read by the app — SMTP is configured per-organization from the admin UI after login, not via environment variables.

### Security

- Patched fixable CVEs in base container images and tuned Trivy CI scanning (`ignore-unfixed`), cutting code-scanning noise from ~971 alerts down to the handful that are actually actionable.

### Added

- `demo.irdoc.io` seed data and a 6-hourly automated reset script for the public demo environment.

### Changed

- The frontend Docker image is no longer published for `linux/arm64` — a Vite/Rollup arm64 native dependency deadlocks installing under this project's CI QEMU emulation. The image is static, nginx-served content and runs fine on an arm64 host under its own amd64 emulation if needed. The backend image is unaffected and still ships both `linux/amd64` and `linux/arm64`.

### Internal

- Release image tagging now strips a leading `v` from the git tag, so `docker-compose.prod.yml`'s `VERSION` value actually matches the published image tag.
- Added a 30-minute timeout to the Docker build-and-push CI job, so a hung build step fails within 30 minutes instead of silently running for up to GitHub's 6-hour default.

## [0.1.0-alpha] - 2026-09-10

### Added

**Core incident workspace**
- Timeline-first incident workspace with entry types: detection, analysis, containment, evidence, comms, note
- Incident lifecycle management with severity (Sev 1–4) and status (open, contained, monitoring, closed)
- Auto-generated incident references (`INC-YYYY-NNNN`) with external ref tracking (SDP, Jira, ManageEngine, ServiceNow)
- Keyboard shortcut `N` to focus Add Entry form; `Escape` to close modals

**IOC management**
- IOC tracking: IP, domain, email, URL, hash, file, username with confidence scores (0–100) and TLP levels
- Auto-detect IOCs from pasted text — surface all contained IOCs with bulk-add modal
- Status tracking: active, blocked, remediated, false positive

**Evidence and attachments**
- Drag-and-drop file attachments on timeline entries
- Global paste handler — paste screenshots anywhere on the page to attach to the current entry
- SHA-256 integrity hash computed and stored for every attachment
- Signed URL serving — files never exposed directly from web root

**Tasks**
- Phase-grouped task management (Identification, Containment, Eradication, Recovery, Post-Incident)
- Incident templates: phishing, credential compromise, malware infection, suspicious login
- Optimistic task toggle with rollback on failure

**Inbound webhook API**
- `POST /api/v1/external/incidents` — create cases from any tool that can POST JSON
- API key authentication with scoped permissions (`incidents:create`, `timeline:read`, etc.)
- Rate limited: 20 requests/min per key, 64KB max payload

**Report generation**
- Schema-driven report template builder — compose reports visually as ordered block arrays
- Block types: cover, section, stat_row, timeline, ioc_table, task_list, evidence_register, text_block, divider, page_break, header, tag_list
- System templates: Management Brief, Technical Report, Legal/Compliance
- Export formats: Markdown, HTML (core); PDF, DOCX (premium)
- One-click report generation with async Celery pipeline

**Investigation graph**
- Visual relationship map between IOCs, timeline entries, and evidence (React Flow)
- Manual edge creation by dragging between nodes
- Node detail panel with enrichment summary
- networkx server-side hierarchical layout

**Integrations**
- IOC enrichment: VirusTotal, AbuseIPDB, Shodan
- SIEM: Microsoft Sentinel
- EDR: CrowdStrike
- IAM: Azure Active Directory
- Comms: Slack, Microsoft Teams
- Ticketing: Jira
- Alerting: PagerDuty
- Sync: SharePoint (with debounced auto-sync via Redis keyspace notifications)

**AI features (premium)**
- Executive summary generation (Anthropic Claude, OpenAI, Ollama)
- Analyst recommendations
- Provider-agnostic via pluggable protocol

**Multi-tenancy and enterprise (premium)**
- Full org isolation with PostgreSQL row-level security
- RBAC: viewer, analyst, senior_analyst, admin role hierarchy
- User invite system (48h token, email delivery)
- SSO / SAML 2.0 (Okta, Azure AD, Google Workspace, any SAML IdP)
- Immutable audit log with 8 filter dimensions and CSV export
- Cloud storage backends: S3-compatible (MinIO, Wasabi, Cloudflare R2), Azure Blob, Google Cloud Storage

**Admin panel**
- Team management: invite, role change, deactivate (last-admin guard)
- Org settings: name, registration policy, custom branding
- Storage backend configuration and live switching
- Incident template editor
- Audit log browser with CSV export
- SSO configuration (IdP metadata, attribute mapping, role mappings)

**Infrastructure**
- Docker Compose deployment (dev + production variants)
- Nginx reverse proxy with full security header suite (HSTS, CSP, X-Frame-Options, Permissions-Policy)
- Multi-arch Docker images: `linux/amd64` + `linux/arm64`
- GitHub Actions CI/CD: lint → audit → test → build → push
- One-command upgrade script with zero-downtime migration
- Backup and restore scripts with 30-day rotation
- Redis `notify-keyspace-events Ex` for SharePoint debounce delivery

**Security**
- All queries via SQLAlchemy ORM — no raw SQL
- Argon2id password and API key hashing
- Fernet symmetric encryption for stored credentials (integration configs, storage configs)
- JWT access token in-memory only (never localStorage); refresh token in HttpOnly SameSite=Strict cookie
- Rate limiting: auth 5/min, webhook 20/min per key, API 100/min (slowapi)
- MIME validation and 50MB upload limit
- UUID-based storage paths (no user input in file paths)
- `pip-audit` and `npm audit` in CI pipeline

---

[Unreleased]: https://github.com/soc-irdoc/irdoc-app/compare/v0.1.1-alpha...main
[0.1.1-alpha]: https://github.com/soc-irdoc/irdoc-app/compare/v0.1.0-alpha...v0.1.1-alpha
[0.1.0-alpha]: https://github.com/soc-irdoc/irdoc-app/releases/tag/v0.1.0-alpha
