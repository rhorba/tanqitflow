# Metrics Log — TanqitFlow

---

## Sprint 10 — 2026-06-26

**Coverage**: 81.73% (Sprint 9 gate) — no new backend logic added in Sprint 10
**Stories completed**: 10.1, 10.2, 10.3, 10.4, 10.5
**Story points**: ~26 SP delivered

### Files changed
- `docker-compose.prod.yml` — resource limits, api healthcheck, driver:local volumes
- `.env.example` — added REDIS_PASSWORD
- `nginx/nginx.conf` — docs route passes through to FastAPI (JWT-gated)
- `api/main.py` — DocsAuthMiddleware, openapi_tags, TanqitFlow API v1.0 title
- `api/routers/*.py` — summary + description on all endpoints
- `.github/workflows/pr.yml` — new PR validation pipeline
- `.github/workflows/deploy.yml` — new main pipeline: lint+test → SAST → build+push → DAST → SSH deploy
- `frontend/Dockerfile.prod` — multi-stage nginx production build
- `frontend/nginx.conf` — SPA serving config for prod container
- `frontend/tests/e2e/v1-recording.spec.ts` — v1.0 critical flows recording spec
- `docs/deployment-guide.md` — full VPS deployment guide
- `scripts/record-v1.sh` — recording helper script

### Sprint 10 snapshot
| Metric | Value |
|--------|-------|
| Test coverage | 81.73% (held from Sprint 9) |
| API endpoints documented | 100% (summary + description) |
| CI/CD pipelines | 3 (ci.yml, pr.yml, deploy.yml + security.yml) |
| Docker image targets | 2 (api, frontend) |
| GHCR registry | ghcr.io/rhorba/tanqitflow-{api,frontend} |
| Git tag | v1.0 |
