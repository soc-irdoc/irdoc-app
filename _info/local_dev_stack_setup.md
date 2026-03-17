# Local Development Environment Setup

**Stack:** React 18 + TypeScript + Vite \| FastAPI \| PostgreSQL 16 \|
Redis \| Celery \| Nginx \| Docker Compose \| Ollama (optional local AI)

This guide walks you step‑by‑step through installing everything required
to develop and run the full stack locally.

------------------------------------------------------------------------

# 1. Install Core Prerequisites

## 1.1 Install Git

Download: https://git-scm.com/downloads

Verify installation:

``` bash
git --version
```

------------------------------------------------------------------------

## 1.2 Install Docker Desktop

Docker will run: - PostgreSQL - Redis - Nginx - Ollama - backend -
frontend

Download:

https://www.docker.com/products/docker-desktop/

After installing verify:

``` bash
docker --version
docker compose version
```

Make sure **Docker Desktop is running**.

------------------------------------------------------------------------

## 1.3 Install Node.js (LTS)

Download:

https://nodejs.org/

Verify:

``` bash
node -v
npm -v
```

------------------------------------------------------------------------

## 1.4 Install Python 3.11+

Download:

https://www.python.org/downloads/

Verify:

``` bash
python --version
pip --version
```

------------------------------------------------------------------------

## 1.5 Install Visual Studio Code

Download:

https://code.visualstudio.com/

Recommended extensions:

    Python
    Pylance
    Docker
    ESLint
    Prettier
    PostgreSQL
    Thunder Client
    GitLens

------------------------------------------------------------------------

# 2. Create the Project Structure

Create a workspace folder:

``` bash
mkdir my-ai-app
cd my-ai-app
```

Structure:

    my-ai-app
    │
    ├── backend
    │   ├── app
    │   ├── alembic
    │   └── requirements.txt
    │
    ├── frontend
    │
    ├── nginx
    │   └── nginx.conf
    │
    ├── docker
    │   └── Dockerfile.backend
    │
    └── docker-compose.yml

------------------------------------------------------------------------

# 3. Setup the React Frontend

Create React app using **Vite**.

``` bash
npm create vite@latest frontend
```

Select:

    React
    TypeScript

Install dependencies:

``` bash
cd frontend
npm install
```

Run development server:

``` bash
npm run dev
```

Frontend will run on:

    http://localhost:5173

------------------------------------------------------------------------

# 4. Setup FastAPI Backend

Go to backend folder:

``` bash
cd ../backend
```

Create virtual environment:

``` bash
python -m venv venv
```

Activate it:

Windows:

``` bash
venv\Scripts\activate
```

Linux/macOS:

``` bash
source venv/bin/activate
```

Install dependencies:

``` bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary alembic redis celery pydantic python-dotenv
```

Save dependencies:

``` bash
pip freeze > requirements.txt
```

------------------------------------------------------------------------

# 5. Setup PostgreSQL (Docker)

We will run PostgreSQL inside Docker.

Example docker-compose service:

``` yaml
postgres:
  image: postgres:16
  environment:
    POSTGRES_USER: app
    POSTGRES_PASSWORD: app
    POSTGRES_DB: appdb
  ports:
    - "5432:5432"
  volumes:
    - postgres_data:/var/lib/postgresql/data
```

Connect using:

    host: localhost
    port: 5432
    user: app
    password: app
    database: appdb

------------------------------------------------------------------------

# 6. Setup SQLAlchemy

Install driver:

``` bash
pip install psycopg2-binary
```

Example connection string:

    postgresql+psycopg2://app:app@localhost:5432/appdb

------------------------------------------------------------------------

# 7. Setup Alembic (Database Migrations)

Initialize Alembic:

``` bash
alembic init alembic
```

Edit:

    alembic.ini

Set database URL.

Create first migration:

``` bash
alembic revision --autogenerate -m "init"
```

Run migration:

``` bash
alembic upgrade head
```

------------------------------------------------------------------------

# 8. Setup Redis

Redis is required for:

-   Celery task queue
-   pub/sub
-   caching

Docker service:

``` yaml
redis:
  image: redis:7
  ports:
    - "6379:6379"
```

Test connection:

``` bash
redis-cli ping
```

Expected response:

    PONG

------------------------------------------------------------------------

# 9. Setup Celery Workers

Install Celery:

``` bash
pip install celery redis
```

Example start worker:

``` bash
celery -A app.worker worker --loglevel=info
```

------------------------------------------------------------------------

# 10. Setup Ollama (Local AI)

Ollama allows running local LLMs.

Download:

https://ollama.com/download

Run server:

``` bash
ollama serve
```

Pull a model:

``` bash
ollama pull llama3
```

Test:

``` bash
ollama run llama3
```

Optional Docker service:

``` yaml
ollama:
  image: ollama/ollama
  ports:
    - "11434:11434"
  volumes:
    - ollama:/root/.ollama
```

------------------------------------------------------------------------

# 11. Setup Nginx

Create `nginx/nginx.conf`

Example:

``` nginx
events {}

http {

    server {

        listen 80;

        location /api {
            proxy_pass http://backend:8000;
        }

        location / {
            proxy_pass http://frontend:5173;
        }

    }

}
```

------------------------------------------------------------------------

# 12. Create Dockerfile for Backend

`docker/Dockerfile.backend`

``` dockerfile
FROM python:3.11

WORKDIR /app

COPY backend/requirements.txt .

RUN pip install -r requirements.txt

COPY backend /app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

------------------------------------------------------------------------

# 13. Create docker-compose.yml

``` yaml
version: "3.9"

services:

  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: appdb
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  backend:
    build:
      context: .
      dockerfile: docker/Dockerfile.backend
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  nginx:
    image: nginx:latest
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

------------------------------------------------------------------------

# 14. Run the Full Stack

Start everything:

``` bash
docker compose up --build
```

Services:

  Service    URL
  ---------- ----------------------------
  Frontend   http://localhost:5173
  Backend    http://localhost:8000
  API Docs   http://localhost:8000/docs
  Postgres   localhost:5432
  Redis      localhost:6379

------------------------------------------------------------------------

# 15. Recommended Developer Tools

### Database GUI

DBeaver

https://dbeaver.io/

### API Testing

Thunder Client (VS Code extension)

### Container UI

Portainer

### Code Formatting

Frontend:

    Prettier
    ESLint

Backend:

    black
    ruff

------------------------------------------------------------------------

# 16. Future Improvements

Add:

-   authentication (JWT / OAuth)
-   background job monitoring (Flower)
-   observability (Prometheus + Grafana)
-   CI/CD pipeline
-   production secrets management
-   S3 compatible storage (MinIO)
-   vector database (pgvector)

------------------------------------------------------------------------

# 17. Quick Start Summary

``` bash
# start services
docker compose up --build

# start frontend dev server
cd frontend
npm run dev

# start backend dev server
cd backend
uvicorn app.main:app --reload
```

------------------------------------------------------------------------

**You now have a full modern AI-ready development stack running
locally.**
