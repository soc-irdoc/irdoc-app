# IRP Phase 6 — Hardening, Performance & Open-Source Launch

> **Status:** Planning  
> **Depends on:** Phase 5 complete  
> **Estimated effort:** 3–4 weeks  
> **Goal:** The platform is production-hardened, performant under realistic SOC load, documented thoroughly, published to GitHub and Docker Hub with a clear upgrade and maintenance path, and ready for public open-source release.

---

## 1. Objectives

By end of Phase 6:
- Zero known high/critical security vulnerabilities
- API responds under P95 targets under realistic SOC load (20 concurrent analysts)
- Docker Hub images published (multi-arch: amd64 + arm64)
- GitHub repository public under AGPL-3.0
- Full user, admin, and developer documentation
- Automated CI/CD: test → lint → security scan → build → push image
- One-command upgrade path verified (with data preserved)
- `CHANGELOG.md` and semantic versioning in place
- Backup and restore procedures tested and documented

---

## 2. Security Hardening

### 2.1 OWASP Top 10 Checklist

| Risk | Mitigation | Verified By |
|---|---|---|
| SQL Injection | All queries via SQLAlchemy ORM | Code review + sqlmap scan |
| XSS | React escapes by default; bleach sanitizes HTML in reports | Automated + manual |
| CSRF | SameSite=Strict cookies; no cookie-only mutation paths | Code review |
| Auth bypass | JWT signature + expiry enforced; refresh token rotation | pytest auth suite |
| IDOR | All queries filter by `org_id`; RLS as safety net; ownership checks in services | pytest + manual |
| File upload abuse | MIME validation; 50MB limit; UUID paths; outside web root; signed URLs | pytest |
| Path traversal | Storage paths are UUID-based — no user input in paths | Code review |
| Rate limiting | slowapi: auth (5/min), external webhook (20/min), API (100/min) | Load test |
| Secrets exposure | `.env` only; never in logs, responses, or exception messages | grep CI check |
| Vulnerable deps | pip-audit + npm audit in CI; Dependabot on repo | CI pipeline |

### 2.2 Security Headers (Nginx)

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "
  default-src 'self';
  script-src 'self';
  style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
  font-src 'self' https://fonts.gstatic.com;
  img-src 'self' data: blob:;
  connect-src 'self' wss: https:;
" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
```

Validate with securityheaders.com — target grade A.

### 2.3 Input Sanitization

All user-provided text that appears in generated HTML reports is sanitized server-side:

```python
import bleach

ALLOWED_TAGS = ['b', 'i', 'u', 'em', 'strong', 'br', 'p', 'ul', 'ol', 'li', 'code', 'pre']

def sanitize_html(text: str) -> str:
    return bleach.clean(text, tags=ALLOWED_TAGS, attributes={}, strip=True)
```

### 2.4 Container Hardening

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

# Run as non-root
RUN useradd --create-home --shell /bin/bash irpapp
USER irpapp

# Read-only filesystem where possible
# Secrets never baked into image — all from env vars at runtime
```

---

## 3. Performance Optimization

### 3.1 Database Indexes (Final Verification)

Run `EXPLAIN ANALYZE` on the 10 most common production query patterns. All must use indexes — no seq scans on tables larger than 1,000 rows.

Critical queries to verify:
1. `GET /incidents` — filter by org_id + status + severity
2. `GET /incidents/{id}/timeline` — filter by incident_id, ordered by occurred_at
3. `GET /incidents/{id}/iocs` — filter by incident_id + status
4. `GET /incidents/{id}/tasks` — filter by incident_id, group by phase
5. `GET /audit-log` — filter by org_id + created_at range
6. `GET /incidents/{id}/graph` — join timeline_entries + iocs + ioc_timeline_links
7. Full-text search on `timeline_entries.description`

### 3.2 API Response Time Targets

| Endpoint | P50 | P95 |
|---|---|---|
| `GET /incidents` (50 rows) | < 50ms | < 100ms |
| `GET /incidents/{id}/timeline` | < 80ms | < 150ms |
| `POST /timeline` (add entry) | < 100ms | < 200ms |
| `GET /incidents/{id}/graph` | < 200ms | < 400ms |
| `GET /incidents/{id}/stats` | < 50ms | < 100ms |
| `POST /external/incidents` (inbound webhook) | < 150ms | < 300ms |

### 3.3 Caching

```python
# Redis cache — short TTLs for live data, longer for rarely-changing data

@cache(ttl=30,  key="incident:{id}:stats")
async def get_incident_stats(incident_id): ...

@cache(ttl=300, key="features:{org_id}")
async def get_feature_flags(org_id): ...

@cache(ttl=60,  key="incident:{id}:graph")
async def get_graph(incident_id): ...

@cache(ttl=120, key="report_templates:{org_id}")
async def list_report_templates(org_id): ...
```

Cache is invalidated on relevant writes (incident update clears stats cache, etc.).

### 3.4 Frontend Bundle

```
Targets:
  Initial JS bundle:       < 200KB gzipped
  First Contentful Paint:  < 1.5s (standard workstation, LAN)
  Time to Interactive:     < 3s

Techniques:
  - Vite route-based code splitting (each page is its own chunk)
  - React.lazy() for heavy components (ReactFlow graph, report builder canvas)
  - @tanstack/react-virtual for timeline lists > 100 entries
  - Google Fonts preloaded via <link rel="preload">
```

### 3.5 Load Test

Simulated scenario using k6 or Locust before launch:

```
Scenario: Realistic SOC workload
  - 20 concurrent analysts
  - Each adding 1 timeline entry every 5 minutes
  - IOC lookups: 1 per analyst per 2 minutes
  - Report generation: 1 per incident per 30 minutes
  - 5 incidents active simultaneously
  Run duration: 30 minutes

Pass criteria:
  - P95 response times within targets above
  - CPU < 70% sustained
  - Memory stable (no leak over 30 min)
  - Zero 5xx errors
  - Zero failed SharePoint syncs due to timeout

Test environment: 4 vCPU, 8GB RAM (typical self-hosted VM)
```

---

## 4. Docker Hub Publishing

### 4.1 Images

```
irpdoc/irpdoc-backend:latest
irpdoc/irpdoc-backend:1.0.0
irpdoc/irpdoc-frontend:latest
irpdoc/irpdoc-frontend:1.0.0
```

Multi-arch builds: `linux/amd64` (servers) + `linux/arm64` (Apple Silicon development, ARM cloud instances).

### 4.2 Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.9'

x-backend-env: &backend-env
  DATABASE_URL: ${DATABASE_URL}
  REDIS_URL: ${REDIS_URL}
  SECRET_KEY: ${SECRET_KEY}
  STORAGE_BACKEND: ${STORAGE_BACKEND:-local}
  STORAGE_PATH: /app/storage
  BASE_URL: ${BASE_URL}
  LICENSE_KEY: ${LICENSE_KEY:-}
  AI_BACKEND: ${AI_BACKEND:-}
  EMAIL_BACKEND: ${EMAIL_BACKEND:-console}

services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: irp
      POSTGRES_USER: irp
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U irp"]
      interval: 10s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD} --notify-keyspace-events Ex --save 60 1
    volumes:
      - redis_data:/data

  backend:
    image: irpdoc/irpdoc-backend:${VERSION:-latest}
    restart: unless-stopped
    environment: *backend-env
    volumes:
      - ./storage:/app/storage
    depends_on:
      db:
        condition: service_healthy
    expose:
      - "8000"

  worker:
    image: irpdoc/irpdoc-backend:${VERSION:-latest}
    restart: unless-stopped
    command: celery -A app.workers.celery_app worker -c 4 --loglevel=warning
    environment: *backend-env
    volumes:
      - ./storage:/app/storage
    depends_on: [db, redis]

  beat:
    image: irpdoc/irpdoc-backend:${VERSION:-latest}
    restart: unless-stopped
    command: celery -A app.workers.celery_app beat --loglevel=warning
    environment: *backend-env
    depends_on: [db, redis]

  frontend:
    image: irpdoc/irpdoc-frontend:${VERSION:-latest}
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./ssl:/etc/nginx/ssl:ro
    depends_on: [backend]

volumes:
  postgres_data:
  redis_data:
```

Note: `notify-keyspace-events Ex` is set on Redis to enable keyspace notifications for the SharePoint debounce expiry mechanism.

### 4.3 Upgrade Script (One Command)

```bash
#!/bin/bash
# upgrade.sh
set -e

echo "=== IRDoc Upgrade ==="
echo "Pulling latest images..."
docker compose -f docker-compose.prod.yml pull

echo "Running database migrations..."
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

echo "Restarting services..."
docker compose -f docker-compose.prod.yml up -d --remove-orphans

echo "Upgrade complete."
docker compose -f docker-compose.prod.yml exec backend python -c \
  "from app import __version__; print(f'Running version: {__version__}')"
```

**Migration compatibility rule:** Every Alembic migration must be backward-compatible with the previous image version. No column drops, no NOT NULL additions without defaults, no table renames — these are done in two-migration steps. This guarantees a rolling upgrade without downtime.

---

## 5. CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_DB: irp_test, POSTGRES_USER: irp, POSTGRES_PASSWORD: test }
        options: --health-cmd pg_isready --health-interval 10s
      redis:
        image: redis:7
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r backend/requirements.txt
      - run: pip-audit                         # security: fail on high/critical
      - run: cd backend && ruff check .        # lint
      - run: cd backend && pytest --cov=app --cov-report=xml -v
      - run: |                                 # secret leak check
          grep -r "irp_key_\|sk-ant-\|AKIA" backend/app/ && exit 1 || exit 0

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd frontend && npm ci
      - run: cd frontend && npm audit --audit-level=high
      - run: cd frontend && npm run type-check
      - run: cd frontend && npm run lint
      - run: cd frontend && npm run build

  build-and-push:
    needs: [test-backend, test-frontend]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          context: ./backend
          platforms: linux/amd64,linux/arm64
          push: true
          tags: |
            irpdoc/irpdoc-backend:latest
            irpdoc/irpdoc-backend:${{ github.sha }}
      - uses: docker/build-push-action@v5
        with:
          context: ./frontend
          platforms: linux/amd64,linux/arm64
          push: true
          tags: |
            irpdoc/irpdoc-frontend:latest
            irpdoc/irpdoc-frontend:${{ github.sha }}

  release:
    needs: [build-and-push]
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Tag Docker images with version
        run: |
          VERSION=${GITHUB_REF#refs/tags/}
          docker buildx imagetools create \
            --tag irpdoc/irpdoc-backend:${VERSION} \
            irpdoc/irpdoc-backend:${{ github.sha }}
      - uses: softprops/action-gh-release@v1
        with:
          body_path: CHANGELOG.md
          files: docker-compose.prod.yml
```

---

## 6. Documentation

### 6.1 Docs Site (MkDocs + Material Theme)

```
docs/
├── index.md                       # Overview + 5-minute quickstart
├── installation/
│   ├── docker-compose.md          # Standard self-hosted
│   ├── environment-variables.md   # All .env options
│   ├── upgrading.md               # Upgrade procedure
│   └── backup-restore.md
├── user-guide/
│   ├── creating-incidents.md
│   ├── timeline.md                # Add entries, paste screenshots, attachments
│   ├── ioc-management.md          # Add IOCs, enrichment, bulk import
│   ├── report-template-builder.md # Visual builder walkthrough
│   ├── generating-reports.md
│   ├── sharepoint-sync.md         # Setting up auto-sync
│   ├── tasks-and-templates.md
│   └── keyboard-shortcuts.md
├── admin-guide/
│   ├── user-management.md         # Invites, roles, SSO
│   ├── storage-backends.md        # S3, Azure Blob, GCS setup + migration notes
│   ├── api-keys.md                # Creating keys for SDP/ManageEngine/Jira
│   ├── integrations/
│   │   ├── virustotal.md
│   │   ├── sentinel.md
│   │   ├── crowdstrike.md
│   │   ├── azuread.md
│   │   ├── sharepoint.md
│   │   ├── slack.md
│   │   └── servicedesk-plus.md    # SDP inbound webhook setup guide
│   ├── sso-saml.md
│   └── licensing.md
├── api/
│   └── reference.md               # Links to /api/docs (auto-generated)
├── contributing/
│   ├── development-setup.md
│   ├── architecture.md
│   └── adding-integrations.md     # How to write a new plugin
└── changelog.md
```

### 6.2 README.md (GitHub)

```markdown
# IRDoc — Incident Response Documentation Platform

> Timeline-first IR documentation with visual report builder, SharePoint auto-sync,
> and AI-assisted summaries.

[![CI](badge)] [![Docker Pulls](badge)] [![License: AGPL-3.0](badge)]

## Quick Start

```bash
git clone https://github.com/irpdoc/irpdoc
cd irpdoc && cp .env.example .env
docker compose up
```

Open http://localhost:3000 — complete first-time setup on first visit.

## What it does
- ⚡ Timeline-first incident workspace
- 🎯 IOC management with auto-enrichment (VirusTotal, AbuseIPDB)
- 📋 Visual report template builder — compose reports for management, legal, analysts
- 📤 SharePoint auto-sync — management always has a current document, no manual effort
- 🎫 Service desk integration — create cases from SDP, ManageEngine, Jira via API
- 🤖 AI executive summaries (premium)
- 🔌 Integrations: Sentinel, CrowdStrike, Entra, Slack, Proofpoint
- 💾 Pluggable storage — local, S3, Azure Blob, GCS (cloud = premium)
- 🔒 Self-hosted — your incident data stays on your infrastructure

## License
Core: AGPL-3.0 | Premium features require a license key
See [LICENSE-COMMERCIAL.md](LICENSE-COMMERCIAL.md) for pricing.
```

---

## 7. Versioning & Release Process

**Semantic versioning:** `MAJOR.MINOR.PATCH`
- `MAJOR`: Breaking API changes
- `MINOR`: New features (new integration, new block type, new storage backend)
- `PATCH`: Bug fixes, security patches

**Security patches:** released within 24 hours of discovery for critical CVEs.

**Changelog format:** [Keep a Changelog](https://keepachangelog.com/)

```markdown
## [1.0.0] - 2026-04-XX
### Added
- Timeline-first incident workspace
- Visual report template builder with 11 block types
- SharePoint auto-sync with debounced delivery
- Inbound webhook API for ServiceDesk Plus, ManageEngine, Jira
- IOC enrichment via VirusTotal and AbuseIPDB
- Integrations: Sentinel, CrowdStrike, Azure AD, Slack, Teams
- Pluggable storage backends: local, S3-compatible, Azure Blob, GCS
- Investigation graph (React Flow)
- AI executive summaries and recommendations (premium)
- Multi-tenancy with PostgreSQL row-level security
- SSO / SAML 2.0 (premium)
- Full audit log (premium)
- Docker Compose deployment, single-command upgrade
```

---

## 8. Backup & Restore

### Backup Script

```bash
#!/bin/bash
# backup.sh — run via cron (daily recommended)
set -e

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/opt/irpdoc/backups
mkdir -p ${BACKUP_DIR}

# Database
docker compose exec -T db pg_dump -U irp irp | gzip > ${BACKUP_DIR}/db_${DATE}.sql.gz

# Storage files (local backend only — cloud backends have their own redundancy)
if [ "${STORAGE_BACKEND:-local}" = "local" ]; then
  tar -czf ${BACKUP_DIR}/storage_${DATE}.tar.gz ./storage/
fi

# Rotate: keep 30 days
find ${BACKUP_DIR} -mtime +30 -delete

echo "Backup complete: db_${DATE}.sql.gz"
```

### Restore

```bash
# Restore database
zcat backups/db_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose exec -T db psql -U irp irp

# Restore files (local storage)
tar -xzf backups/storage_YYYYMMDD_HHMMSS.tar.gz -C .

# Restart
docker compose restart backend worker beat
```

**SHA-256 verification after restore:**

```bash
# Verify a sample of file hashes after restore
docker compose exec backend python -c "
from app.services.attachment_service import verify_all_hashes
results = verify_all_hashes(sample_size=100)
print(f'Verified: {results.ok}/{results.total} | Mismatches: {results.mismatches}')
"
```

---

## 9. Post-Launch Maintenance Model

| Task | Frequency | Owner |
|---|---|---|
| Dependency updates (Dependabot) | Weekly (auto-PR) | Reviewer approves |
| Security patch releases | < 24h for critical CVEs | Lead developer |
| Minor feature releases | Monthly | Product + developers |
| Docker image rebuild | Every merge to main | CI/CD (automatic) |
| Docs updates | Per feature release | Developer who built it |
| Community issue triage | Twice weekly | Maintainer rotation |
| Load test re-run | Per minor release | DevOps |

---

## 10. Deliverables Checklist

### Security
- [ ] All OWASP Top 10 items verified
- [ ] Security headers validated (securityheaders.com → grade A)
- [ ] pip-audit: zero high/critical issues
- [ ] npm audit: zero high/critical issues
- [ ] Input sanitization: XSS payloads rejected in report HTML
- [ ] Rate limiting verified on auth and external webhook endpoints
- [ ] Secret leak grep check passing in CI

### Performance
- [ ] All DB indexes verified (EXPLAIN ANALYZE on 10 key queries)
- [ ] P95 response times within targets under 20 concurrent users
- [ ] Frontend bundle < 200KB gzipped
- [ ] Load test passes all criteria

### DevOps
- [ ] Docker Hub images published (backend + frontend, amd64 + arm64)
- [ ] `docker compose up` from scratch completes in < 3 minutes
- [ ] Upgrade script tested: old version → new version, data preserved
- [ ] Backup/restore tested end-to-end (DB + files + hash verification)
- [ ] CI/CD pipeline passing on all PRs
- [ ] Redis `notify-keyspace-events Ex` confirmed active in prod compose

### Documentation
- [ ] README complete with quickstart
- [ ] User guide covers all core workflows including report builder and SharePoint sync
- [ ] Admin guide covers storage backends and inbound webhook setup for SDP/ManageEngine
- [ ] Contributing guide complete
- [ ] API reference at `/api/docs`

### Launch
- [ ] GitHub repository made public
- [ ] Docker Hub images public
- [ ] Initial release tagged `v1.0.0`
- [ ] `CHANGELOG.md` complete for v1.0.0
- [ ] License files correct (AGPL-3.0 core + commercial license text)

---

*End of planning documents — 7 phases from vision to public launch.*
*Return to Phase 0 for the architectural overview and foundational decisions.*
