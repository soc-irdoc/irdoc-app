# Changelog

All notable changes to IRDoc are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
IRDoc uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The current pre-release version is tracked in [`VERSION`](VERSION).

---

## [Unreleased]

### Fixed

- **Reports not regenerated after incident changes** — auto-regeneration only existed as two integration-specific pipelines (AI, and SharePoint-without-AI), so on an install with neither enabled, editing an incident never produced a new report version. Even where it existed: AI orgs only regenerated templates flagged `ai_auto_generate`; AI + SharePoint orgs never regenerated or pushed unflagged templates; and the SharePoint debounce fired only if the 10-second beat scan happened to land in the key's last ~2 seconds, so most triggers were silently dropped. Replaced with a single debounced pipeline (`report_regen_service` + `auto_regenerate_reports`): once any report has been generated for an incident, every later change to it (fields, timeline, IOCs, tasks, assets, asset links, attachments) queues one new version of each template already used, including the base report. AI narrative and SharePoint push are applied per version when enabled. The debounce is now a trailing-edge token check on the scheduled task instead of a beat scan. Timeline deletes, IOC edits/deletes, task deletes, attachments and asset links now trigger regeneration too. (#58)
- **Report version stuck at v1 for non-AI reports** — `version_number` was only computed inside `generate_report`'s AI branch. Versions are now assigned per (incident, template) when the report is created, for manual and automatic reports alike, and the reports table shows the version for every report. (#58)

## [0.1.2-alpha] - 2026-09-22

### Fixed

- **Incident tabs and left-nav frozen after the first click** — `react-router-dom` v7's `<BrowserRouter>` now wraps every location update in `React.startTransition()` by default. Under React 18, that transition-wrapped update to `<Routes>` could be starved by other synchronous re-renders in the tree (zustand/WebSocket-driven state on the incident workspace page) and never commit, even though `history.pushState`/`replaceState` had already changed the URL — so a tab or nav click changed the address bar but left the previous screen on-screen, and every navigation afterwards (any tab, any nav item) stayed stuck until a full page reload. Fixed by opting out with `useTransitions={false}`, restoring synchronous route updates. (#48)
- **`beat` container always reporting unhealthy** — its healthcheck shells out to `pgrep`, which isn't part of the `python:3.12-slim-bookworm` base image (no `procps`); it has failed with `pgrep: not found` (exit 127) every 30s since the healthcheck was added, even though the `celery beat` process itself was running fine. Added `procps` to `backend/Dockerfile`. (#49)
- **Report generation failing with `'function' object has no attribute '_fail_on_errors'` whenever the report template had a logo** — WeasyPrint 70.0 (picked up in the CVE-2026-55073 patch bump from 62.3) removed `weasyprint.urls.default_url_fetcher` in favour of a `URLFetcher` class, and now reads `url_fetcher._fail_on_errors` whenever a fetch raises. The renderer's data-URI-only fetcher was still a plain function calling the removed API, so it raised `ImportError` on every call and WeasyPrint then blew up reading `_fail_on_errors` off a function. It only surfaced once a document actually referenced a resource — i.e. only for templates carrying an uploaded logo, which is stored as a base64 `data:` URI; logo-less reports never called the fetcher and rendered fine. Replaced with a `URLFetcher(allowed_protocols=("data",))` instance, which keeps the same SSRF / local-file-disclosure guard natively. (#50)
- **Strict CSP blocking the SPA's own assets** — the nginx policy (`default-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'`) set no `style-src`, `img-src`, `font-src` or `connect-src`, so all four fell back to `'self'` and the browser blocked the webfont stylesheet, the editor's injected `<style>` tag, and every `data:`/`blob:` preview — including the logo preview on the report-template editor. The policy now declares `style-src 'self' 'unsafe-inline'` (TipTap/ProseMirror injects a `<style>` tag at runtime and nginx serves `index.html` statically, so a nonce isn't available), `img-src 'self' data: blob:`, `font-src 'self'` and `base-uri 'self'`, while `script-src` stays `'self'` with no `'unsafe-inline'`/`'unsafe-eval'`. Fixed in both the installer's nginx generator (`installer/core/ssl.py`, which is what real installs render) and the static `docker/nginx/nginx.demo-https.conf`. (#51)
- **New timeline entries saved off by the browser's UTC offset** — the "add entry" form built `occurred_at` as a naive `${date}T${time}` string with no timezone offset and sent it as-is. The column is `timestamptz` under a UTC database session, so the local wall-clock time the form displayed (e.g. `19:57:03`) was stored as if it were already UTC, then correctly converted back to local for display — silently re-adding the offset a second time (e.g. `22:57:03` in UTC+3) on every read. The entry-edit form already converted correctly via `new Date(...).toISOString()`; the add-entry form now matches it. (#52)

### Changed

- **Webfonts are now self-hosted** instead of being loaded from `fonts.googleapis.com`. IRDoc is deployed on-prem and frequently air-gapped, where the external stylesheet silently fell back to system fonts; self-hosting also removes a third-party origin from the CSP and stops leaking viewer IPs to Google. Adds `@fontsource/syne` and `@fontsource/jetbrains-mono`; every Google subset is still declared with its `unicode-range`, so browsers download only the glyph ranges a page actually uses (Vite is now told never to inline font files — its 4KB default was embedding the small Greek/Cyrillic/Vietnamese subsets into the main stylesheet as `data:` URIs, which shipped them to every visitor and tripped `font-src` as well).

### Internal

- **CI's backend test job was intermittently failing with `out of shared memory` / `increase max_locks_per_transaction`** — the test suite's `setup_db` fixture drops and recreates the full ~28-table schema before every single test; measured directly, one cycle holds ~361 locks in one transaction, which reproducibly exhausted Postgres's default shared lock-table budget partway through a run and cascaded into failing every later test too. Raised `max_locks_per_transaction` to 1024 for CI's `postgres:16-alpine` service (via `POSTGRES_INITDB_ARGS`, the only way to set a postmaster-context setting on a service container). (#54)
- **A second, unrelated CI failure: `RuntimeError: ... attached to a different loop`** — `test_mfa_admin.py` and `test_mfa_verify.py` were marked `@pytest.mark.anyio` instead of `@pytest.mark.asyncio`, the only two files in the suite doing so; this ran them on a different event loop than `pytest-asyncio`'s shared one, corrupting the test suite's shared DB connection pool and taking two unrelated tests down with it. (#54)
- **`npm audit` in CI was failing on vitest/vite/esbuild advisories** that only affect devDependencies never shipped in the production bundle. Scoped the audit to `--omit=dev`, matching how the backend's `pip-audit` step already handles an accepted, unfixable finding rather than disabling the check outright. (#54)

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
