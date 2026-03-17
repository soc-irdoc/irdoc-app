# Development Setup

---

## Prerequisites

- Python 3.12
- Node.js 20+
- Docker and Docker Compose (for PostgreSQL + Redis)
- Git

---

## Clone and configure

```bash
git clone https://github.com/soc-irdoc/irdoc-app
cd irdoc-app
cp .env.example .env
```

Edit `.env`:
- Set `DB_PASSWORD`, `REDIS_PASSWORD`, `SECRET_KEY`
- Leave `BASE_URL=http://localhost:3000`
- Leave `EMAIL_BACKEND=console`

---

## Start infrastructure

```bash
cd docker
docker compose up db redis -d
```

This starts only PostgreSQL and Redis (not the app services).

---

## Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate         # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run migrations and seed data
alembic upgrade head
python seed.py

# Start development server
uvicorn app.main:app --reload --port 8000
```

API is now available at http://localhost:8000. OpenAPI docs: http://localhost:8000/api/docs.

---

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend is now at http://localhost:3000. Vite proxies `/api` and `/socket.io` to `:8000`.

---

## Running Tests

```bash
cd backend
pytest -v                        # all tests
pytest tests/unit/ -v            # unit tests only (no DB needed)
pytest tests/integration/ -v     # integration tests (SQLite in-memory)
pytest --cov=app --cov-report=term-missing  # with coverage
```

### Test setup notes

- Integration tests use SQLite in-memory (no PostgreSQL needed)
- The `conftest.py` provides `admin_user` and `auth_headers` fixtures
- Unit tests are pure Python — run instantly without any infrastructure

---

## Linting

```bash
# Backend
cd backend && ruff check .
cd backend && ruff check . --fix   # auto-fix

# Frontend
cd frontend && npm run lint
cd frontend && npm run type-check
```

---

## Security audit

```bash
# Backend
pip-audit --requirement backend/requirements.txt

# Frontend
cd frontend && npm audit
```

---

## Celery workers (optional for development)

Most features work without Celery in development. For report generation, enrichment, and SharePoint sync, start the worker:

```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=debug
```

---

## Development with Docker

If you prefer to run everything in Docker:

```bash
cd docker
docker compose up
```

This builds and starts all services including the frontend.

To see backend logs: `docker compose logs -f backend`
To run a one-off command: `docker compose exec backend alembic upgrade head`
