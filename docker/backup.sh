#!/bin/bash
# backup.sh — IRDoc backup script (recommended: run via cron daily)
# Usage: bash backup.sh
# Backups are written to ./backups/ and rotated after 30 days.
set -e

COMPOSE_FILE="$(dirname "$0")/docker-compose.prod.yml"
BACKUP_DIR="$(dirname "$0")/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "${BACKUP_DIR}"

echo "=== IRDoc Backup — ${DATE} ==="

# ── Database ──────────────────────────────────────────────────────────────────
echo "[1/3] Backing up database..."
docker compose -f "${COMPOSE_FILE}" exec -T db \
  pg_dump -U irp irp | gzip > "${BACKUP_DIR}/db_${DATE}.sql.gz"
echo "      Saved: db_${DATE}.sql.gz"

# ── Storage files (local backend only) ───────────────────────────────────────
STORAGE_BACKEND="${STORAGE_BACKEND:-local}"
if [ "${STORAGE_BACKEND}" = "local" ]; then
  echo "[2/3] Backing up local storage files..."
  STORAGE_DIR="$(dirname "$0")/storage"
  if [ -d "${STORAGE_DIR}" ]; then
    tar -czf "${BACKUP_DIR}/storage_${DATE}.tar.gz" -C "$(dirname "${STORAGE_DIR}")" "$(basename "${STORAGE_DIR}")"
    echo "      Saved: storage_${DATE}.tar.gz"
  else
    echo "      Storage directory not found — skipping."
  fi
else
  echo "[2/3] Cloud storage backend (${STORAGE_BACKEND}) — files managed by provider, skipping local backup."
fi

# ── Rotate old backups (keep 30 days) ────────────────────────────────────────
echo "[3/3] Rotating backups older than 30 days..."
find "${BACKUP_DIR}" -name "*.sql.gz" -mtime +30 -delete
find "${BACKUP_DIR}" -name "*.tar.gz" -mtime +30 -delete

echo ""
echo "Backup complete."
echo "Location: ${BACKUP_DIR}"
echo ""
echo "To restore:"
echo "  DB:      zcat ${BACKUP_DIR}/db_${DATE}.sql.gz | docker compose -f docker-compose.prod.yml exec -T db psql -U irp irp"
echo "  Files:   tar -xzf ${BACKUP_DIR}/storage_${DATE}.tar.gz -C $(dirname "$0")"
