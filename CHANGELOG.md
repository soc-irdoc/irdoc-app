# Changelog

All notable changes to IRDoc are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
IRDoc uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The current pre-release version is tracked in [`VERSION`](VERSION). Nothing
below has been tagged as a release yet — it will move under a version
heading here once it is.

---

## [Unreleased]

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

[Unreleased]: https://github.com/soc-irdoc/irdoc-app/commits/main
