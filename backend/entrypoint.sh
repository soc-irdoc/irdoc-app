#!/bin/bash
set -e

# Fix bind-mount ownership, then drop to the unprivileged user.
# docker/storage and docker/backups are bind-mounted from the host. When they
# don't exist yet, Docker creates them owned by root, and the app (uid irp)
# then fails with "Permission denied" the first time it writes a report,
# attachment, backup or the beat schedule (#80). The image therefore starts
# as root only long enough to hand those two directories to irp, and re-execs
# this script as irp. If the container was started as a non-root user
# (e.g. `user:` in compose), skip straight to the normal startup.
if [ "$(id -u)" = "0" ]; then
    for dir in /app/storage /app/backups; do
        mkdir -p "$dir"
        find "$dir" \! -user irp -exec chown irp:irp {} + 2>/dev/null \
            || echo "WARNING: could not change ownership of $dir - writes may fail" >&2
    done
    # setpriv keeps root's environment; HOME=/root makes asyncpg fail probing
    # /root/.postgresql for client certs, so hand over irp's own HOME.
    HOME="$(getent passwd irp | cut -d: -f6)" \
        exec setpriv --reuid=irp --regid=irp --init-groups "$0" "$@"
fi

echo "=== IRDoc Backend Starting ==="

# Wait for PostgreSQL and Redis (belt-and-suspenders - compose healthchecks
# handle the primary wait). Keeps waiting while they start up, but exits
# with a clear message when retrying can't help - a wrong password in
# DATABASE_URL / REDIS_URL, a missing database - instead of looping forever
# (#159). Gives up after WAIT_FOR_SERVICES_TIMEOUT seconds (default 300).
python -m app.cli.wait_for_services

# Run Alembic migrations
echo "Running database migrations..."
alembic upgrade head

# Seed database on first run
echo "Running seed script..."
python seed.py

# Start the application - if a command was passed (worker/beat), run it; otherwise start uvicorn
if [ $# -gt 0 ]; then
    exec "$@"
else
    echo "Starting uvicorn..."
    exec uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 1 \
        --loop uvloop \
        --access-log \
        --log-level info
fi
