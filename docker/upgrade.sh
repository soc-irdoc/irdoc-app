#!/bin/bash
# upgrade.sh — Zero-downtime IRDoc upgrade
# Usage: bash upgrade.sh [version]
# Example: bash upgrade.sh 1.1.0
#          bash upgrade.sh          (upgrades to latest)
set -e

VERSION=${1:-latest}
COMPOSE_FILE="$(dirname "$0")/docker-compose.prod.yml"

echo "=== IRDoc Upgrade ==="
echo "Target version: ${VERSION}"
echo ""

echo "[1/4] Pulling images..."
VERSION=${VERSION} docker compose -f "${COMPOSE_FILE}" pull

echo "[2/4] Running database migrations..."
VERSION=${VERSION} docker compose -f "${COMPOSE_FILE}" run --rm backend alembic upgrade head

echo "[3/4] Restarting services..."
VERSION=${VERSION} docker compose -f "${COMPOSE_FILE}" up -d --remove-orphans

echo "[4/4] Verifying deployment..."
sleep 5
VERSION=${VERSION} docker compose -f "${COMPOSE_FILE}" exec -T backend \
  python -c "from app import __version__; print(f'Running version: {__version__}')"

echo ""
echo "Upgrade complete."
