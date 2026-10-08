#!/bin/bash
# upgrade.sh — Zero-downtime IRDoc upgrade (published images from GHCR)
# Usage: bash upgrade.sh [version]
# Example: bash upgrade.sh 0.1.4-alpha
#          bash upgrade.sh          (upgrades to latest)
#
# Only for installs started with docker-compose.prod.yml (the installer wizard
# and the production guide both do this). An install started with plain
# `docker compose up` (docker-compose.yml) builds from the source checkout:
# it serves on port 3000 and keeps files in the repo-root storage/ directory.
# Upgrading that with this script would silently move it to a different
# stack (ports 80/443, docker/storage/) — so the script refuses (#82).
set -e

VERSION=${1:-latest}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.prod.yml"

echo "=== IRDoc Upgrade ==="
echo "Target version: ${VERSION}"
echo ""

# ── Which compose file is the running install using? ─────────────────────────
running_files=$(docker inspect irdoc-backend \
  --format '{{ index .Config.Labels "com.docker.compose.project.config_files" }}' 2>/dev/null || true)
if [ -n "${running_files}" ] && [[ "${running_files}" != *docker-compose.prod.yml* ]]; then
  cat >&2 <<EOF
This IRDoc install was started from source with:
  ${running_files}

upgrade.sh only upgrades installs that run the published images
(docker-compose.prod.yml). Nothing has been changed.

To update a source install, from the directory you cloned:
  git pull
  cd docker && docker compose up -d --build

If you downloaded a ZIP instead of cloning, switch to a git clone (or the
installer wizard) so updates are possible — see
https://docs.irdoc.io/installation/upgrading
EOF
  exit 1
fi

echo "[1/4] Pulling images..."
VERSION=${VERSION} docker compose -f "${COMPOSE_FILE}" pull

echo "[2/4] Running database migrations..."
VERSION=${VERSION} docker compose -f "${COMPOSE_FILE}" run --rm backend alembic upgrade head

echo "[3/4] Restarting services..."
VERSION=${VERSION} docker compose -f "${COMPOSE_FILE}" up -d --remove-orphans

echo "[4/4] Verifying deployment..."
healthy=false
for _ in $(seq 1 30); do
  if VERSION=${VERSION} docker compose -f "${COMPOSE_FILE}" exec -T backend \
      curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
    healthy=true
    break
  fi
  sleep 2
done
if [ "${healthy}" != true ]; then
  echo "Backend did not become healthy within 60s. Check: docker compose -f docker-compose.prod.yml logs backend" >&2
  exit 1
fi
VERSION=${VERSION} docker compose -f "${COMPOSE_FILE}" exec -T backend \
  python -c "from app import __version__; print(f'Running version: {__version__}')"

echo ""
echo "Upgrade complete."
