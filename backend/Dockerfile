FROM python:3.14-slim-bookworm@sha256:9ab8d9c8514b44f90cf0029dd42fdd7e9e211e639c8b995304cc04568dee900f

# ── Non-root user (security hardening) ─────────────────────────────────────────
RUN groupadd -r irp && useradd -r -g irp irp

# ── System deps for WeasyPrint + asyncpg + pg_dump ─────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libglib2.0-0 \
    gcc \
    curl \
    gnupg \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
       | gpg --dearmor -o /usr/share/keyrings/postgresql-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/postgresql-archive-keyring.gpg] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
       > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-16 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python dependencies ─────────────────────────────────────────────────────────
COPY requirements.lock.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.lock.txt

# ── Application code ────────────────────────────────────────────────────────────
COPY . .

# ── Storage directory ────────────────────────────────────────────────────────────
RUN mkdir -p /app/storage && chown -R irp:irp /app/storage
RUN mkdir -p /app/backups && chown -R irp:irp /app/backups

# ── Entrypoint ──────────────────────────────────────────────────────────────────
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown irp:irp /entrypoint.sh

USER irp

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
