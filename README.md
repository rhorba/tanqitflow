# TanqitFlow

**NRW Intelligence Platform** — Non-Revenue Water analytics for Moroccan water utilities (ONEE & SRM distributors).

[![CI](https://github.com/rhorba/tanqitflow/actions/workflows/ci.yml/badge.svg)](https://github.com/rhorba/tanqitflow/actions/workflows/ci.yml)

---

## Quick Start (Development)

**Prerequisites**: Docker Desktop, Git

```bash
# 1. Clone
git clone https://github.com/rhorba/tanqitflow.git
cd tanqitflow

# 2. Configure environment
cp .env.example .env
# Edit .env — fill in POSTGRES_PASSWORD, JWT_SECRET, PII_ENCRYPTION_KEY, MINIO_ROOT_PASSWORD

# 3. Start all services
docker compose -f docker-compose.dev.yml up --build

# 4. Run DB migrations (first time only)
docker compose -f docker-compose.dev.yml exec api alembic upgrade head

# 5. Access
#   API:          http://localhost:8000
#   API Docs:     http://localhost:8000/docs
#   Frontend:     http://localhost:3000
#   MinIO Console: http://localhost:9001
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2 (async) |
| Database | PostgreSQL 16 · TimescaleDB · PostGIS |
| Task Queue | Celery 5 · Redis 7 |
| Object Storage | MinIO (S3-compatible) |
| Frontend | React 18 · Vite · TypeScript · Tailwind CSS |
| Maps | Leaflet · PostGIS GeoJSON |
| Charts | Recharts |
| i18n | i18next — French + Arabic (RTL) |
| ML | scikit-learn Isolation Forest |
| CI/CD | GitHub Actions |
| Deployment | Docker Compose |

---

## Project Structure

```
tanqitflow/
├── api/           # FastAPI backend
├── frontend/      # React + Vite frontend
├── nginx/         # Nginx config (prod only)
├── docs/          # PRD, architecture, sprint backlog
└── .logs/         # CTS session & activity logs
```

---

## Running Tests

```bash
# Backend (from /api)
docker compose -f docker-compose.dev.yml exec api pytest --cov=. --cov-report=term-missing

# Frontend lint
docker compose -f docker-compose.dev.yml exec frontend npm run lint
```

---

## Documentation

- [PRD](docs/prd-tanqitflow.md)
- [System Design](docs/system-design-tanqitflow.md)
- [Architecture](docs/architecture-tanqitflow.md)
- [Sprint Backlog](docs/stories-tanqitflow.md)
