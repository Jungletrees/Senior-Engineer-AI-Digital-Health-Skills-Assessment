# Local Setup

## Prerequisites

- Docker Engine 24+ (last verified locally on Docker 29.3.1)
- Docker Compose v2+
- Node 20+ only for running frontend commands outside Docker
- Python 3.12 only for running backend or gold-standard commands outside Docker

On Windows, use Docker Desktop with WSL2 integration and keep the repository inside the WSL2 filesystem for better build performance.

## Setup

```sh
git clone <your-fork-url>
cd Senior-Engineer-AI-Digital-Health-Skills-Assessment
cp .env.example .env
docker compose -p assessment up -d --build
```

If the database volume is new or has been reset, run migrations:

```sh
docker compose -p assessment exec backend alembic upgrade head
```

## Services

| Service | URL | Description |
|---|---|---|
| Frontend | http://localhost:3000 | Project status page and entry point |
| Documents UI | http://localhost:3000/documents | PDF upload and document management |
| Chainlit | http://localhost:8000 | Chat UI wired to FastAPI `/api/v1/chat` |
| Backend API | http://localhost:6100 | FastAPI backend |
| Backend health | http://localhost:6100/health | App and database health |
| Backend docs | http://localhost:6100/docs | OpenAPI documentation |
| PostgreSQL | localhost:5432 | PostgreSQL 16 with pgvector |

## Verifying the Setup

```sh
docker compose -p assessment ps
curl -s http://localhost:6100/health
curl -I http://localhost:6100/docs
curl -I http://localhost:3000
curl -I http://localhost:3000/documents
curl -I http://localhost:8000
docker compose -p assessment exec -T relational_db pg_isready -U postgres
```

Expected backend health response:

```json
{"status":"ok","database":"ok"}
```

Document-management API calls are public in the local reviewer stack:

```sh
curl -s http://localhost:6100/api/v1/documents
```

No IAM provider, hosted auth provider, browser token, or bearer header is required for upload/list/status/delete document routes. `/api/v1/auth/session` remains available only if you disable anonymous chat with `ANONYMOUS_CHAT_ALLOWED=false`.

Run the browser smoke after the stack is healthy:

```sh
npm install --prefix frontend
npm --prefix frontend run playwright:install
PLAYWRIGHT_BASE_URL=http://localhost:3000 npm --prefix frontend run test:e2e
```

## Known Build Notes

The backend image installs `poppler-utils` and `tesseract-ocr` at the system layer for PDF rasterization and OCR. The Docker build also pins CPU-only torch before `sentence-transformers` to avoid CUDA wheel downloads.

The Chainlit dependency tree is installed with `uv pip install` in `chainlit_app/Dockerfile`. This avoids long pip resolver backtracking through the Chainlit/OpenTelemetry packages.

## Troubleshooting

**Port already in use**

```sh
ss -ltnp | grep -E ':3000|:8000|:6100|:5432'
```

Stop the conflicting process or remap the port in `docker-compose.yaml`.

**Backend database errors**

```sh
docker compose -p assessment exec backend alembic upgrade head
docker compose -p assessment logs backend
```

**Build fails or seems stuck**

```sh
docker compose -p assessment build backend
docker compose -p assessment build chainlit
docker compose -p assessment build frontend
```

**Container exits immediately**

```sh
docker compose -p assessment logs <service>
```

Service names are `frontend`, `chainlit`, `backend`, and `relational_db`.

## Shutdown

```sh
docker compose -p assessment down
```
