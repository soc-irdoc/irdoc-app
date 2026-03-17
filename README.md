# IRDoc — Incident Response Documentation Platform

> Timeline-first IR documentation with visual report builder, SharePoint auto-sync, and AI-assisted summaries.

[![CI](https://github.com/soc-irdoc/irdoc-app/actions/workflows/ci.yml/badge.svg)](https://github.com/soc-irdoc/irdoc-app/actions/workflows/ci.yml)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL_3.0-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-hub-blue)](https://hub.docker.com/u/soc-irdoc)

---

## What is IRDoc?

IRDoc is a **self-hostable, open-core incident response documentation platform** built for SOC analysts, IR engineers, and MSSPs.

It gives your team a single structured workspace to document an incident from first detection to final report — without switching between a ticket system, a Word document, and a SharePoint folder.

**Core promise:** *Document incidents the way you actually investigate them — fast, structured, and reportable in one click.*

---

## Features

### Core (AGPL-3.0, free forever)
- **Timeline-first workspace** — chronological event log with entry types (detection, analysis, containment, evidence, comms, note)
- **IOC management** — track IPs, domains, hashes, emails, URLs with confidence scores and status
- **Auto-detect IOCs** — paste a block of text and IRDoc surfaces all contained IOCs
- **Evidence attachments** — drag-and-drop or paste screenshots directly into timeline entries
- **Task management** — phase-grouped tasks instantiated from incident templates
- **Inbound webhook API** — create cases from ServiceDesk Plus, ManageEngine, Jira, or any tool that can POST JSON
- **Basic reports** — Markdown and HTML export
- **Investigation graph** — visual relationship map between IOCs, timeline entries, and evidence
- **REST API** — full OpenAPI docs at `/api/docs`
- **Self-hosted** — your incident data stays on your infrastructure

### Premium (commercial license key required)
- **Visual report template builder** — compose management, analyst, and legal report layouts with drag-and-drop blocks
- **PDF and DOCX export** — one-click professional reports from any template
- **SharePoint auto-sync** — management always has a current document, zero manual effort
- **AI executive summaries** — powered by Anthropic Claude, OpenAI, or a local Ollama model
- **IOC enrichment** — automated lookups via VirusTotal, AbuseIPDB, and Shodan
- **SIEM/EDR integrations** — Microsoft Sentinel, CrowdStrike, Azure AD
- **Comms integrations** — Slack, Microsoft Teams, PagerDuty
- **Cloud storage** — S3-compatible (MinIO, Wasabi, R2), Azure Blob, Google Cloud Storage
- **Multi-tenancy** — full org isolation with PostgreSQL row-level security (MSSP mode)
- **SSO / SAML 2.0** — Okta, Azure AD, Google Workspace, any SAML 2.0 IdP
- **Audit log** — immutable record of all actions with CSV export
- **Custom branding** — logo and color scheme per org

---

## Quick Start

**Prerequisites:** Docker and Docker Compose (Docker Desktop on Mac/Windows).

```bash
git clone https://github.com/soc-irdoc/irdoc-app
cd irdoc-app
cp .env.example .env
# Edit .env — set DB_PASSWORD, REDIS_PASSWORD, SECRET_KEY (see instructions inside)
cd docker
docker compose up
```

Open **http://localhost:3000** in your browser.

On first visit, complete the setup wizard to create your admin account.

> Default seed credentials (if setup wizard was skipped): `admin@localhost` / `ChangeMe123!`
> You will be forced to change the password on first login.

---

## Production Deployment

For a production deployment with pre-built Docker Hub images:

```bash
git clone https://github.com/soc-irdoc/irdoc-app
cd irdoc-app
cp .env.example .env
# Edit .env — set all required values, set ALLOW_REGISTRATION=false
cd docker
docker compose -f docker-compose.prod.yml up -d
```

See [docs/installation/docker-compose.md](docs/installation/docker-compose.md) for the full production guide including TLS/SSL setup.

### Upgrading

```bash
cd docker
bash upgrade.sh           # upgrade to latest
bash upgrade.sh 1.1.0     # upgrade to specific version
```

The upgrade script: pulls new images → runs Alembic migrations → restarts services.
All migrations are backward-compatible — zero-downtime rolling upgrades are supported.

### Backup

```bash
cd docker
bash backup.sh
```

Backs up the PostgreSQL database and (optionally) local storage files. Rotates backups older than 30 days.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Nginx (reverse proxy + static files)                   │
│  React 18 + TypeScript + Vite frontend                  │
├─────────────────────────────────────────────────────────┤
│  FastAPI (Python 3.12) — async REST API + WebSocket     │
│  SQLAlchemy 2 ORM  ·  Pydantic v2  ·  Redis pub/sub    │
├─────────────────────────────────────────────────────────┤
│  Celery workers — reports, enrichment, SharePoint sync  │
├─────────────┬───────────────────────────────────────────┤
│  PostgreSQL │  Redis 7                                  │
│  (JSONB,    │  (Celery broker, debounce, pub/sub)       │
│   RLS, FTS) │                                           │
└─────────────┴───────────────────────────────────────────┘
```

**Storage:** Pluggable `StorageBackend` protocol. Switch between local filesystem, S3-compatible, Azure Blob, and GCS without code changes — switchable from the admin panel at runtime.

**Reports:** Schema-driven, not hardcoded templates. Users compose reports visually as an ordered array of block types (cover, timeline, IOC table, stat rows, etc.). The renderer iterates blocks and assembles Jinja2 partials.

**Integrations:** Plugin system — each integration is a single file with a `config_schema` that the frontend renders as a form automatically. Adding a new integration requires only a new plugin file.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic v2, Celery |
| Database | PostgreSQL 16 (JSONB, tsvector FTS, row-level security) |
| Cache/Queue | Redis 7 |
| Frontend | React 18, TypeScript, Vite, Zustand, TanStack Query |
| Reports | Jinja2, WeasyPrint (PDF), python-docx (DOCX) |
| Auth | JWT (access token in-memory), Argon2id, SAML 2.0 |
| Graph | React Flow (`@xyflow/react`), networkx layout |
| Deployment | Docker, Docker Compose, Nginx |

---

## Configuration

All configuration is via environment variables in `.env`. See [docs/installation/environment-variables.md](docs/installation/environment-variables.md) for the full reference.

Key variables:

| Variable | Description |
|---|---|
| `SECRET_KEY` | JWT signing key — generate with `openssl rand -hex 32` |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `BASE_URL` | Public URL of your deployment (e.g. `https://irdoc.example.com`) |
| `LICENSE_KEY` | Commercial license key (leave empty for core features only) |
| `AI_BACKEND` | `anthropic` \| `openai` \| `ollama` |
| `EMAIL_BACKEND` | `console` \| `smtp` |
| `ALLOW_REGISTRATION` | `true` (dev) \| `false` (prod — use invites) |

---

## Inbound Webhook (ServiceDesk Plus / ManageEngine / Jira)

Create an API key in Settings → API Keys with the `incidents:create` scope, then configure your service desk tool to POST to:

```
POST https://your-irdoc/api/v1/external/incidents
Authorization: ApiKey irp_key_your_key_here
Content-Type: application/json

{
  "title": "Suspicious login alert — user john.doe@corp.com",
  "severity": "sev2",
  "external_source": "servicedesk_plus",
  "external_ref": "SDP-18423",
  "external_url": "https://sdp.corp.com/WorkOrder.do?woMode=viewWO&woID=18423"
}
```

The case appears in IRDoc immediately with a clickable badge linking back to the source ticket.

See [docs/admin-guide/integrations/servicedesk-plus.md](docs/admin-guide/integrations/servicedesk-plus.md) for the full setup guide.

---

## Development Setup

```bash
# Clone
git clone https://github.com/soc-irdoc/irdoc-app && cd irdoc-app

# Backend (Python 3.12)
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # edit values
# Start PostgreSQL and Redis (via docker compose or locally)
uvicorn app.main:app --reload

# Frontend
cd ../frontend
npm install
npm run dev

# Tests
cd ../backend
pytest -v
```

See [docs/contributing/development-setup.md](docs/contributing/development-setup.md) for the full development guide.

---

## Adding an Integration

IRDoc uses a plugin system — add a new integration in a single file:

```python
# backend/app/plugins/integrations/my_tool.py
from ..registry import register_plugin
from ..base import BasePlugin

@register_plugin
class MyToolPlugin(BasePlugin):
    name = "my_tool"
    display_name = "My Tool"
    category = "ti"          # ti | siem | edr | iam | comms | storage_sync
    is_premium = True
    config_schema = {
        "api_key": {"type": "string", "label": "API Key", "secret": True},
        "base_url": {"type": "string", "label": "Base URL"},
    }

    async def enrich(self, ioc_value: str, ioc_type: str) -> dict:
        # Call your API, return enrichment data
        ...
```

The frontend automatically renders the `config_schema` as a form in the Integrations admin panel. No frontend changes needed.

See [docs/contributing/adding-integrations.md](docs/contributing/adding-integrations.md).

---

## License

**Core** (this repository): [AGPL-3.0](LICENSE)

**Premium features** require a commercial license key. See [LICENSE-COMMERCIAL.md](LICENSE-COMMERCIAL.md) for pricing and terms.

Premium features are always visible in the UI with a lock overlay — you can see what you would get before purchasing. They are never hidden entirely.

---

## Security

If you discover a security vulnerability, please report it via email to **security@irpdoc.io** rather than opening a public issue.

We aim to release security patches within 24 hours of discovery for critical CVEs.

---

## Contributing

Contributions are welcome. Please read [docs/contributing/development-setup.md](docs/contributing/development-setup.md) before opening a PR.

- Bug reports and feature requests: [GitHub Issues](https://github.com/soc-irdoc/irdoc-app/issues)
- Security vulnerabilities: security@irpdoc.io (do not open public issues)
