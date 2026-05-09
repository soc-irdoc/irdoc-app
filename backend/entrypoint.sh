#!/bin/bash
set -e

echo "=== IRDoc Backend Starting ==="

# Wait for DB to be ready (belt-and-suspenders — compose healthcheck handles primary wait)
until python -c "
import asyncio, sys
import asyncpg
async def check():
    try:
        conn = await asyncpg.connect('${DATABASE_URL}'.replace('+asyncpg', ''))
        await conn.close()
    except Exception as e:
        print(f'DB not ready: {e}', file=sys.stderr)
        sys.exit(1)
asyncio.run(check())
" 2>/dev/null; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done

echo "PostgreSQL ready."

# Run Alembic migrations
echo "Running database migrations..."
alembic upgrade head

# Seed database on first run
echo "Running seed script..."
python seed.py

# Start the application — if a command was passed (worker/beat), run it; otherwise start uvicorn
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
