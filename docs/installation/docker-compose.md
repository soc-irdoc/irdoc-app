# Docker Compose Setup

This is the recommended way to deploy IRDoc.

---

## Prerequisites

- Docker Engine 24+ and Docker Compose V2
- 2 vCPU, 4GB RAM minimum (4 vCPU, 8GB recommended for production)
- Outbound internet access for pulling images and enrichment API calls

---

## Development (build from source)

```bash
git clone https://github.com/soc-irdoc/irdoc-app
cd irdoc-app
cp .env.example .env
```

Edit `.env` — at minimum set:
- `DB_PASSWORD` — strong random password for PostgreSQL
- `REDIS_PASSWORD` — strong random password for Redis
- `SECRET_KEY` — generate with `openssl rand -hex 32`

```bash
cd docker
docker compose up
```

Open http://localhost:3000 and complete the first-run setup.

---

## Production (pre-built images from Docker Hub)

```bash
git clone https://github.com/soc-irdoc/irdoc-app
cd irdoc-app
cp .env.example .env
```

Edit `.env`:
- Set `DB_PASSWORD`, `REDIS_PASSWORD`, `SECRET_KEY` (strong values)
- Set `BASE_URL` to your public domain (e.g. `https://irdoc.example.com`)
- Set `ALLOW_REGISTRATION=false` — require invites in production
- Set `EMAIL_BACKEND=smtp` and configure SMTP settings for invite emails

```bash
cd docker
docker compose -f docker-compose.prod.yml up -d
```

---

## TLS / HTTPS

The production nginx container serves HTTPS if you provide SSL certificates:

```bash
mkdir -p docker/ssl
# Place your certificate files:
#   docker/ssl/cert.pem
#   docker/ssl/key.pem
```

Then update `docker/nginx/nginx.conf` to add an HTTPS server block:

```nginx
server {
    listen 443 ssl;
    ssl_certificate     /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    # ... rest of config
}
```

For Let's Encrypt, use [certbot](https://certbot.eff.org/) or [Caddy](https://caddyserver.com/) as an alternative reverse proxy.

---

## Services

| Service | Description | Port |
|---|---|---|
| `frontend` | Nginx serving React app + proxy | 3000 (dev) / 80,443 (prod) |
| `backend` | FastAPI application server | 8000 (internal) |
| `worker` | Celery task worker | — |
| `beat` | Celery periodic task scheduler | — |
| `db` | PostgreSQL 16 | 5432 (internal) |
| `redis` | Redis 7 | 6379 (internal) |

In production, only the `frontend` service exposes ports externally. All other services communicate on the internal Docker network.

---

## Data Persistence

Persistent data is stored in Docker named volumes:
- `postgres_data` — all incident data, users, reports
- `redis_data` — Celery queue state, pub/sub

Local storage files (evidence, generated reports) are mounted from `./storage/` on the host.

**Back these up regularly.** See [Backup & Restore](backup-restore.md).

---

## Checking the deployment

```bash
# View all service logs
docker compose logs -f

# Check a specific service
docker compose logs -f backend

# Verify the backend is healthy
curl http://localhost:8000/api/health
```

Expected health response: `{"status": "ok", "version": "1.0.0"}`
