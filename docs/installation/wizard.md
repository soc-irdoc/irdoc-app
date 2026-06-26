# Installation & Upgrade Wizard

The IrDoc wizard is a browser-based setup assistant that walks you through installing or upgrading IrDoc without touching any config files by hand. It handles TLS certificates, secrets generation, database migrations, and health checks — and creates a full backup before every upgrade so you can roll back with one click if something goes wrong.

---

## Before You Start

**System requirements**

| Requirement | Minimum |
|---|---|
| Python | 3.10 or later |
| Docker Engine | 24 or later |
| Docker Compose | V2 plugin (comes bundled with Docker Desktop and Docker Engine 24+) |
| RAM | 4 GB (8 GB recommended for production) |
| CPU | 2 vCPU (4 vCPU recommended) |
| Disk | 10 GB free for the application + additional space for backups |
| Ports | 80 and 443 available on the host |

**Install wizard dependencies** (one-time, from the repo root):

```bash
pip install -r installer/requirements.txt
```

---

## Starting the Wizard

Run this command from the **repo root** (the directory that contains the `docker/` and `installer/` folders):

```bash
python3 installer/wizard.py
```

A browser tab opens automatically at `http://127.0.0.1:8888`. If your browser does not open, navigate there manually.

The wizard detects what it needs to do:

| Situation | Wizard mode |
|---|---|
| No `docker/.env` file found | **Fresh install** |
| `docker/.env` exists and running version matches the repo | **Reconfigure** (re-runs install flow with your existing secrets pre-filled) |
| `docker/.env` exists but the running version is different (or no container is running) | **Upgrade** |

---

## Fresh Install

### Step 1 — Prerequisites check

The wizard scans your system and reports any problems before touching anything.

**Blocking issues** (must be fixed before continuing):

- Python 3.10 or later is not found
- Docker Engine is not installed
- Docker Compose V2 plugin is missing
- Docker daemon is not running — fix with `sudo systemctl start docker`
- The `docker/` directory is missing (means you're running from the wrong directory)

**Warnings** (you can proceed, but should investigate):

- Port 443 is already in use — something else may be listening on HTTPS
- Port 80 is already in use

If any blocking issue is shown, the **Continue** button is disabled. Fix the issue and refresh the page.

---

### Step 2 — HTTPS / TLS configuration

Choose how IrDoc will serve HTTPS:

**Option A — Import a certificate (PFX)**

Use this if your organisation has issued a TLS certificate for the IrDoc hostname.

- Upload the `.pfx` or `.p12` file
- Enter the passphrase (leave blank if the file has no passphrase)
- The wizard extracts the certificate and private key and shows you the Common Name and expiry date

**Option B — Generate a self-signed certificate**

Use this for internal deployments where you control the trust store, or for a quick test.

- Enter the hostname (Common Name) — defaults to the machine's fully-qualified domain name
- Optionally add Subject Alternative Names (SANs): additional hostnames or IP addresses, comma-separated
- The wizard generates a 2-year certificate immediately

> **Note:** Browsers will show a security warning for self-signed certificates. To silence it, add the generated certificate to your OS or browser trust store.

**Option C — Behind a load balancer / reverse proxy**

Use this when TLS is terminated upstream (an Nginx, HAProxy, Cloudflare, or AWS ALB in front of IrDoc) and IrDoc only needs to listen on HTTP internally.

- No certificate is needed
- Nginx is configured to listen on port 80 and trust the `X-Forwarded-For` header from your upstream proxy
- HSTS is still set so that browsers enforce HTTPS end-to-end

---

### Step 3 — Core configuration

| Field | Description | Default |
|---|---|---|
| Base URL | The public URL users will type into their browser (e.g. `https://irdoc.example.com`) | `https://<hostname>` |
| Database password | Password for the internal PostgreSQL database | Auto-generated (32 random chars) |
| Redis password | Password for the internal Redis instance | Auto-generated (32 random chars) |
| Secret key | Used to sign authentication tokens | Auto-generated (64 hex chars) |
| Access token lifetime | How long a login session stays valid before requiring re-authentication | 15 minutes |
| Refresh token lifetime | How long a "remember me" token remains valid | 30 days |
| License key | Your IrDoc license key (leave blank for Community edition) | — |

The wizard auto-generates strong random values for passwords and the secret key. You can click **Regenerate** to get new values, or type your own. Store these values somewhere safe — they are written to `docker/.env` and are not shown again after installation.

---

### Step 4 — Admin account

Create the first administrator account for IrDoc.

| Field | Requirement |
|---|---|
| Name | Any display name |
| Email | Used to log in |
| Password | Minimum 12 characters |

This account is created automatically when deployment completes. You can create additional users and admins from the Admin panel after logging in.

---

### Step 5 — Review

A summary page shows everything that will be written before any files are touched:

- HTTPS mode and certificate details (CN, expiry, SANs)
- Base URL
- Token lifetimes
- Admin account email

Click **Confirm & Deploy** to proceed. At this point the wizard writes three things to disk:

- `docker/.env` — all secrets and configuration (permissions: `0600`, owner-read-only)
- `docker/nginx/nginx.conf` — generated nginx configuration for your chosen HTTPS mode
- `docker/ssl/cert.pem` and `docker/ssl/key.pem` (only when you imported or generated a certificate; key file permissions: `0600`)

---

### Step 6 — Deployment

The wizard streams live output for each stage:

| Stage | What happens |
|---|---|
| Pulling images | Downloads the IrDoc backend and frontend Docker images |
| Starting containers | Runs `docker compose up -d` with the new configuration |
| Health check | Polls `GET /api/health` every 3 seconds until it returns `200` (up to 2 minutes) |
| Creating admin account | Calls `POST /api/v1/auth/setup` with the admin credentials you entered |

If any stage fails, the error is shown inline and the wizard stops. The most common causes:

- Image pull fails: no internet access or Docker Hub rate limit — retry, or pull manually with `docker compose -f docker/docker-compose.prod.yml pull`
- Health check times out: the backend is slow to start — wait a moment and check `docker compose logs irdoc-backend`
- Admin creation fails with `409`: the setup endpoint has already been used — log in with the credentials you entered

---

### Step 7 — Done

Once all stages complete, the success screen shows your IrDoc URL. Click it to open IrDoc and log in with the admin account you created.

The wizard process exits automatically after 2 seconds.

---

## Upgrade

When the wizard detects an existing `docker/.env` and a different running version, it switches to upgrade mode automatically.

### Step 1 — Welcome screen

Displays the current state before anything is changed:

- Running containers and their status
- Available disk space
- Current `storage/` directory size

Review this information and click **Start Upgrade** when ready.

---

### Step 2 — Pre-upgrade snapshot

Before touching anything, the wizard creates a full backup in `backups/pre-upgrade-<timestamp>/`:

| File | Contents |
|---|---|
| `env.bak` | Copy of `docker/.env` |
| `ssl/` | Copy of `docker/ssl/` (certificates) |
| `dump.sql` | Full PostgreSQL dump via `pg_dump` |
| `storage.tar.gz` | All files under `storage/` (evidence, generated reports) |
| `snapshot.json` | Manifest: version info, file list, SHA-256 checksums |

This snapshot is what makes one-click rollback possible. The wizard won't proceed to the next step until the snapshot succeeds.

---

### Step 3 — Upgrade progress

The upgrade runs five sequential steps:

| Step | What happens |
|---|---|
| Pull new images | Downloads images for the target version |
| Stop containers | Stops all running IrDoc containers |
| Run database migrations | Executes `alembic upgrade head` in a temporary container against the stopped database |
| Start containers | Starts containers with the new images |
| Health check | Polls `GET /api/health` until the new version responds |

If the migration step fails, the wizard records the failure point and offers an immediate rollback without waiting for you to click through the rest.

If the health check fails, the same rollback option is offered.

---

### Step 4 — Success (or rollback)

**If the upgrade succeeds:** the success screen shows the new version and the URL. The wizard exits.

**If the upgrade fails:** a rollback screen appears showing the snapshot that was taken. Click **Roll Back** to restore the previous state.

---

## Rollback

Rollback is a seven-step automated process:

| Step | What happens |
|---|---|
| Stop containers | Stops all IrDoc containers |
| Restore database | Drops and recreates the PostgreSQL volume, restores `dump.sql` |
| Restore configuration | Copies `env.bak` back to `docker/.env` |
| Restore SSL certificates | Replaces `docker/ssl/` from the snapshot |
| Restore storage files | Unpacks `storage.tar.gz` over the `storage/` directory |
| Start previous version | Starts containers using the image tag from before the upgrade |
| Health check | Confirms the previous version is responding |

After a successful rollback the previous version is running again and the wizard exits.

**If rollback itself fails**, click **Manual Recovery Instructions** for step-by-step shell commands you can run directly on the host to restore from the snapshot files.

---

## Reconfigure

If you want to change settings (Base URL, token lifetimes, license key) on an already-running installation, start the wizard again:

```bash
python3 installer/wizard.py
```

Because the running version matches the repo version, the wizard enters **reconfigure** mode and pre-fills your existing secrets. Work through the steps as in a fresh install — your passwords and secret key are preserved unless you change them explicitly. Deployment re-applies the configuration without touching the database.

---

## Disabling the automatic update check

On startup the wizard checks the GitHub Releases API for a newer version and shows a banner if one is available. To skip this check (for air-gapped environments or CI pipelines):

```bash
IRDOC_NO_UPDATE_CHECK=1 python3 installer/wizard.py
```

---

## Where files are written

| Path | Description |
|---|---|
| `docker/.env` | All secrets and runtime configuration (0600) |
| `docker/nginx/nginx.conf` | Generated nginx configuration |
| `docker/ssl/cert.pem` | TLS certificate (install / import modes only) |
| `docker/ssl/key.pem` | TLS private key (0600, install / import modes only) |
| `backups/pre-upgrade-<timestamp>/` | Pre-upgrade snapshot directory |

---

## Troubleshooting

**The browser doesn't open automatically**

Navigate to `http://127.0.0.1:8888` manually. If the page doesn't load, check that port 8888 is free:

```bash
# Linux / macOS
lsof -i :8888

# Windows
netstat -ano | findstr :8888
```

**`ModuleNotFoundError: No module named 'httpx'`**

Install the wizard dependencies:

```bash
pip install -r installer/requirements.txt
```

**Prerequisites page shows "Docker daemon running: No"**

Start the Docker daemon:

```bash
# Linux
sudo systemctl start docker

# macOS / Windows
# Open Docker Desktop
```

**Health check times out after deployment**

The backend may need more time on first start (it runs database initialisation). Wait 30 seconds and check the logs:

```bash
docker compose -f docker/docker-compose.prod.yml logs irdoc-backend --tail=50
```

**Admin creation returns 409**

The admin account was already created (perhaps from a previous partial run). Log in at your Base URL with the credentials you entered — they were accepted the first time.

**Upgrade migration fails**

The migration logs are shown inline. If the error is not clear, run the migration manually to see the full output:

```bash
docker compose -f docker/docker-compose.prod.yml run --rm irdoc-backend alembic upgrade head
```

Then use the wizard's **Roll Back** button to restore the previous state while you investigate.
