# IrDoc Installation & Upgrade Wizard — Design Spec

**Date:** 2026-06-23
**Status:** Approved — ready for implementation planning

---

## Overview

A browser-based installation and upgrade wizard for IrDoc, distributed as a Python script alongside the existing `docker/` directory in the repo. Users run one command on the server; a local web server starts and the browser opens automatically. All configuration, HTTPS setup, and deployment happens through the browser UI — no terminal knowledge required after the initial launch command.

**Launch command:**
```bash
python3 installer/wizard.py
# Browser opens automatically at http://localhost:8888
```

---

## Goals

- Fresh install of IrDoc (Docker Compose) without hand-crafting `.env` files or running `openssl` commands
- HTTPS setup supporting enterprise certificate import (PFX/P12), self-signed generation, and load-balancer passthrough
- Guided upgrade flow with a full point-in-time snapshot and one-click rollback
- Works air-gapped (no CDN, no auto-update, no external dependencies at runtime)
- Professional production release structure distributed via `git clone` + git tags

## Non-Goals

- Configuring integrations (SMTP, SharePoint, Azure AD, AI — handled post-install in Settings)
- Configuring backups (handled post-install in Settings)
- Horizontal scaling or multi-node deployment
- Running the wizard as a Docker container (avoids chicken-and-egg on fresh install)

---

## Tech Stack

| Component | Choice | Reason |
|---|---|---|
| Web framework | FastAPI | Async; native Server-Sent Events for live Docker log streaming |
| Templates | Jinja2 | Server-rendered HTML, no build step |
| Frontend reactivity | Alpine.js | Bundled locally (`static/alpine.js`), no CDN required |
| Styles | Plain CSS | Single hand-crafted `static/style.css`, no Tailwind dependency |
| Certificate handling | `cryptography` (Python) | PFX parsing, self-signed cert generation |
| File uploads | `python-multipart` | PFX file upload in browser |

**Python requirements (`installer/requirements.txt`):**
```
fastapi
uvicorn
jinja2
cryptography
python-multipart
```

Python 3.10+ required. No other host dependencies beyond Docker Engine and Docker Compose V2.

---

## Folder Structure

```
irdoc-app/                        ← repo root (git clone lands here)
  installer/
    wizard.py                     ← FastAPI app + CLI launcher (opens browser)
    core/
      config.py                   ← .env generation, reading existing config
      docker.py                   ← subprocess wrapper for docker compose commands
      ssl.py                      ← PFX parsing, self-signed cert generation
      snapshot.py                 ← pg_dump backup and restore logic
      health.py                   ← health checks against running containers
    templates/                    ← Jinja2 HTML (one file per wizard screen)
      base.html
      prerequisites.html
      https_mode.html
      core_config.html
      admin_user.html
      review.html
      deploy.html
      success.html
      upgrade_welcome.html
      snapshot.html
      upgrade_progress.html
      upgrade_success.html
      rollback.html
    static/
      alpine.js                   ← bundled Alpine.js, no CDN
      style.css
    requirements.txt
  docker/                         ← existing, unchanged structure
    docker-compose.prod.yml       ← updated: name + container_name fields
    docker-compose.yml
    docker-compose.test.yml
    nginx/
      nginx.conf                  ← wizard writes this (HTTP or HTTPS variant)
    ssl/                          ← wizard writes cert.pem + key.pem here
    .env                          ← wizard writes this; never committed
  backend/
  frontend/
  docs/
  VERSION                         ← plain text version string e.g. "1.2.0"
```

The wizard writes **only** to `docker/` — `.env`, `ssl/`, and `nginx/nginx.conf`. It never modifies `backend/` or `frontend/`.

---

## Auto-Detection: Install vs. Upgrade

On startup, the wizard checks one condition:

```
docker/.env exists?
  NO  → Fresh Install mode
  YES → reads VERSION from running irdoc-backend container image tag
        compares to VERSION file in repo root
        if equal   → Reconfigure mode (install flow pre-filled with existing values)
        if differs → Upgrade mode
```

No mode flag needed. Same command every time.

---

## Docker Container Naming

The compose files are updated to use explicit project and container names, replacing the current default `docker-<service>-1` naming.

Applied to both `docker-compose.yml` and `docker-compose.prod.yml`:

```yaml
name: irdoc-app

services:
  db:
    container_name: irdoc-db
  redis:
    container_name: irdoc-redis
  backend:
    container_name: irdoc-backend
  worker:
    container_name: irdoc-worker
  beat:
    container_name: irdoc-beat
  frontend:
    container_name: irdoc-frontend
  ollama:
    container_name: irdoc-ollama
```

**Result in `docker ps`:**
```
irdoc-db
irdoc-redis
irdoc-backend
irdoc-worker
irdoc-beat
irdoc-frontend
```

**Constraint:** `container_name` disables Docker Compose replica scaling for that service. Acceptable for a self-hosted single-node deployment; revisit if horizontal scaling is ever needed.

**Migration note:** Existing installs running with default naming will have their containers renamed on next `docker compose up`. Docker volumes are unaffected (they are named volumes, not container-scoped). The upgrade wizard handles this transparently.

---

## Install Flow

### Step 1 — Prerequisites Check

Runs automatically on wizard load. No user input required.

| Check | Pass condition | On fail |
|---|---|---|
| Python ≥ 3.10 | `sys.version_info >= (3, 10)` | Hard block — show install link |
| Docker Engine installed | `docker --version` exits 0 | Hard block — show install link |
| Docker Compose V2 | `docker compose version` exits 0 | Hard block — show install link |
| Docker daemon running | `docker info` exits 0 | Hard block — show `sudo systemctl start docker` |
| `docker/` directory found | path exists relative to wizard | Hard block — wrong working directory |
| Port 443 free (if not behind LB) | socket bind check | Amber warning — show what's using it |
| Port 80 free | socket bind check | Amber warning only |

Hard blocks prevent advancing. Amber warnings show but allow proceeding.

### Step 2 — HTTPS Mode

User picks one of three cards. Selection determines nginx config generated at deploy time.

**Card A — Import Certificate (PFX/P12)**
- File upload field (`.pfx` / `.p12`)
- Passphrase field (masked)
- On upload: wizard calls `ssl.py` to extract cert + key using `cryptography`
- Shows extracted **Common Name** and **expiry date** for user confirmation
- Writes `docker/ssl/cert.pem` and `docker/ssl/key.pem` at deploy time
- Generates nginx HTTPS server block

**Card B — Generate Self-Signed Certificate**
- Common Name field (pre-filled with `socket.getfqdn()`)
- Subject Alternative Names field (comma-separated IPs/hostnames, optional)
- Validity: 825 days (maximum accepted by modern browsers)
- Generated locally via `cryptography` — no internet required
- Same output as Card A

**Card C — Behind Load Balancer (TLS termination at LB)**
- No certificate required
- Informational note: _"Your load balancer (AVI, F5, etc.) must forward `X-Forwarded-Proto: https` and `X-Forwarded-For` headers"_
- Generates nginx HTTP-only server block with `proxy_set_header` trust directives
- Port 443 not bound by nginx

### Step 3 — Application URL

Single field: **Base URL**

- Pre-filled: `https://<socket.getfqdn()>` (or `http://` if Card C selected)
- Written to `.env` as `BASE_URL`
- Used on the success screen as the clickable app link
- Inline hint: _"Include https:// — no trailing slash"_

### Step 4 — Core Secrets

All three fields auto-generated on page load. Each has a **Regenerate** button and an eye icon to reveal.

| Field | Default | Generation method |
|---|---|---|
| Database Password | 32-char | `secrets.token_urlsafe(24)` |
| Redis Password | 32-char | `secrets.token_urlsafe(24)` |
| Secret Key | 64-char hex | `secrets.token_hex(32)` |

`DATABASE_URL` and `REDIS_URL` are assembled from these values automatically. The full connection strings are shown in a collapsed **Advanced** disclosure only.

**Advanced disclosure** (collapsed by default):
- `ACCESS_TOKEN_EXPIRE_MINUTES` — default 15
- `REFRESH_TOKEN_EXPIRE_DAYS` — default 30
- `ALLOW_REGISTRATION` — locked to `false` with tooltip: _"Users are created via invite after install"_
- `LICENSE_KEY` — empty text field, optional

### Step 5 — First Admin Account

| Field | Validation |
|---|---|
| Full name | Required, max 100 chars |
| Email address | Required, valid email format |
| Password | Required, min 12 chars, inline strength meter |
| Confirm password | Must match password field |

This account is seeded via the backend API during the deploy step (POST to `/api/v1/auth/seed-admin`), not by writing to a config file. The endpoint is only callable once — subsequent calls return 409.

### Step 6 — Review & Deploy

Summary card showing all configured values. Passwords displayed as `••••••••` with reveal toggle.

**Deploy sequence** (each line shown as a live progress row: pending → spinning → ✓ / ✗):

```
① Writing configuration files     docker/.env, nginx.conf, ssl/
② Pulling images                   docker compose pull  [live log stream]
③ Starting containers              docker compose up -d
④ Waiting for health check         GET /api/health  (polls every 3s, 120s timeout)
⑤ Creating admin account           POST /api/v1/auth/seed-admin
```

Live Docker output streams via **Server-Sent Events**. A **"View full logs"** toggle expands the raw output below the progress rows.

On any failure: error log expands inline with a **Copy** button. Deploy halts. User can fix and retry from Step 6 without losing their configuration.

### Success Screen

- Checkmark + version number
- Clickable link to the app (`BASE_URL`)
- Note reminding admin to configure integrations and invite users from Settings

---

## Upgrade Flow

### Step 1 — Upgrade Welcome

Wizard reads current state before any action:

| Info | Source |
|---|---|
| Installed version | `docker inspect irdoc-backend` image tag |
| Target version | `VERSION` file in repo root |
| Container health | `docker compose ps` |
| Available disk space | `shutil.disk_usage('.')` |
| Estimated snapshot size | `du -sh ./storage` + pg_dump size estimate |

**If any container is unhealthy:** amber warning, user must acknowledge before continuing.

**If installed version == target version:** wizard offers **Reconfigure** path instead (install flow with existing values pre-filled).

### Step 2 — Pre-Upgrade Snapshot

Snapshot written to `backups/pre-upgrade-YYYY-MM-DD-HHMMSS/`.

Four progress bars shown simultaneously:

| Task | Output file |
|---|---|
| Configuration backup | `env.bak`, `ssl/` |
| Database dump | `dump.sql` (via `pg_dump` inside irdoc-db container) |
| Storage files | `storage.tar.gz` |
| Snapshot manifest | `snapshot.json` |

`snapshot.json` content:
```json
{
  "version_from": "1.2.0",
  "version_to": "1.3.0",
  "timestamp": "2026-06-23T10:00:00Z",
  "files": ["dump.sql", "env.bak", "ssl/cert.pem", "ssl/key.pem", "storage.tar.gz"],
  "checksums": {
    "dump.sql": "sha256:...",
    "storage.tar.gz": "sha256:..."
  }
}
```

**This step cannot be skipped.** The only exit is cancelling the upgrade entirely.

### Step 3 — Pull New Images

```bash
docker compose -f docker/docker-compose.prod.yml pull
```

Live log stream via SSE. If pull fails (network error, registry auth), upgrade halts here — nothing has changed, no rollback required.

### Step 4 — Stop & Migrate

**4a — Stop containers**
```bash
docker compose -f docker/docker-compose.prod.yml stop
```
Each container stopping shown with spinner → checkmark.

**4b — Run database migrations**
```bash
docker compose -f docker/docker-compose.prod.yml run --rm irdoc-backend alembic upgrade head
```
Live log stream. If migration fails → rollback offered immediately (Step 6).

### Step 5 — Start & Verify

```bash
docker compose -f docker/docker-compose.prod.yml up -d
```

Polls `GET /api/health` every 3 seconds for up to 120 seconds.

**On success → Success screen:**
- Old version → New version
- Total time taken
- Snapshot location (for audit record)
- Link to app
- Note: _"The snapshot at `backups/pre-upgrade-.../` can be deleted once you've verified the upgrade"_

**On health check timeout → Rollback offered (Step 6)**

### Step 6 — Rollback (failure path only)

Shown only when Step 4b (migration) or Step 5 (health check) fails. Never shown on successful upgrade.

Presents snapshot manifest and a single **Roll Back Now** button. On confirm:

```
① Stop all containers
② Drop and recreate database volume
③ Restore database (psql < dump.sql inside a temporary postgres container)
④ Restore docker/.env from snapshot
⑤ Restore docker/ssl/ from snapshot
⑥ Restore storage files
⑦ Start previous version containers (VERSION pinned to version_from)
⑧ Health check
```

Each step shown as a live progress row.

**If rollback itself fails** (disk full, corrupted dump): wizard displays the snapshot path, the exact manual commands to run, and a link to `docs/installation/troubleshooting.md`. It does not attempt further automated recovery.

---

## Wizard Distribution & Versioning

- Wizard lives at `installer/wizard.py` in the repo — same git tag as the app version it ships with
- Version is read from `VERSION` file at repo root (plain text, e.g. `1.2.0`)
- On startup, wizard optionally checks the GitHub Releases API for a newer tag and shows a non-blocking banner if one exists — **never auto-downloads or auto-executes**
- The GitHub check can be disabled (for air-gapped environments) by setting `IRDOC_NO_UPDATE_CHECK=1` in the environment
- For upgrades: user does `git pull && git checkout v1.3.0` then re-runs `python3 installer/wizard.py`

---

## Security Constraints

- Wizard server binds to `127.0.0.1:8888` only — not accessible from other hosts while running
- Wizard should be stopped after install/upgrade completes (exits automatically on success)
- PFX passphrase is never written to disk — only held in memory during extraction
- Generated secrets use Python `secrets` module (cryptographically secure)
- `docker/.env` is written with `chmod 600` (owner read/write only)
- Snapshot directory is written with `chmod 700`

---

## Files Modified in Existing Codebase

| File | Change |
|---|---|
| `docker/docker-compose.prod.yml` | Add `name: irdoc-app` + `container_name:` per service |
| `docker/docker-compose.yml` | Same — keeps dev environment naming consistent |
| `docker/nginx/nginx.conf` | Wizard writes this at deploy time; volume-mounted into the frontend container via the existing `./nginx:/etc/nginx/conf.d` mount in prod compose |
| `VERSION` | New file — plain text version string, committed with each release |
| `backend/app/api/v1/auth.py` | New endpoint: `POST /api/v1/auth/seed-admin` — creates the first admin account; returns 409 if an admin already exists; only callable once |

All other existing files (`backend/`, `frontend/`, existing docs) are unchanged.

**Rollback image pinning:** During rollback, the wizard runs `docker compose up` with `VERSION=<version_from>` passed as an environment variable. Since the compose file uses `image: soc-irdoc/irdoc-backend:${VERSION:-latest}`, this pins containers to the previous version's images, which remain in the local Docker image cache (no re-download required since `docker compose pull` was the only pull and images are not pruned automatically).

---

## Out of Scope (v1)

- SMTP / email configuration (available in Settings → Integrations after install)
- Backup scheduling (available in Settings after install)
- AI, SharePoint, Azure AD, ServiceDesk Plus configuration (all in Settings)
- Multi-node or cluster deployment
- Let's Encrypt / ACME certificate automation
- Windows host support (Linux server assumed; wizard may work on macOS for dev)
