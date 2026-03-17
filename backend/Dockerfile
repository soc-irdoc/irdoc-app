FROM python:3.12-slim-bookworm

# ── Non-root user (security hardening) ─────────────────────────────────────────
RUN groupadd -r irp && useradd -r -g irp irp

# ── System deps for WeasyPrint + asyncpg ───────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libglib2.0-0 \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python dependencies ─────────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ────────────────────────────────────────────────────────────
COPY . .

# ── Storage directory ────────────────────────────────────────────────────────────
RUN mkdir -p /app/storage && chown -R irp:irp /app/storage

# ── Entrypoint ──────────────────────────────────────────────────────────────────
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown irp:irp /entrypoint.sh

USER irp

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
