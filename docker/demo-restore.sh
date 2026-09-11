#!/usr/bin/env bash
# Resets the demo.irdoc.io environment to a fresh, seeded state.
#
# Sequence: stop the app -> destroy the database -> recreate it -> migrate ->
# seed with demo data -> start the app again. Intended to run every 6 hours
# via cron on the demo VPS (see --temp/demo-launch-checklist.md), never on a
# real customer install.
#
# Usage: docker/demo-restore.sh   (run from the repo root, or anywhere —
#        it cd's to its own directory's parent first)
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
COMPOSE_FILE="docker/docker-compose.prod.yml"
COMPOSE=(docker compose -f "$COMPOSE_FILE")

echo "[demo-restore] $(date -Is) — stopping app containers..."
"${COMPOSE[@]}" stop backend worker beat frontend

echo "[demo-restore] destroying the database (and redis) volumes..."
"${COMPOSE[@]}" down -v

echo "[demo-restore] clearing uploaded attachments and old backups..."
rm -rf storage/* backups/*
mkdir -p storage backups

echo "[demo-restore] creating a fresh database..."
"${COMPOSE[@]}" up -d db redis

echo "[demo-restore] applying migrations..."
"${COMPOSE[@]}" run --rm backend alembic upgrade head

echo "[demo-restore] seeding demo data..."
"${COMPOSE[@]}" run --rm backend python seed_demo.py

echo "[demo-restore] starting the app..."
"${COMPOSE[@]}" up -d

echo "[demo-restore] $(date -Is) — done."
