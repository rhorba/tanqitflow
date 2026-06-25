# Decisions Log — TanqitFlow

---

## DEC-001 — Architecture option selected — 2026-06-25

**Decision**: 🔴 COMPREHENSIVE — "Enterprise Hardened"
**Decided by**: Product owner
**Rationale**: Hundreds of DMAs justifies TimescaleDB; Arabic RTL from Sprint 1 avoids expensive retrofit; schema-per-tenant satisfies risk tier 13-15 explicitly called out in brief; MinIO + Isolation Forest + ZAP DAST fit a formal government procurement posture.
**Alternatives rejected**:
- 🟢 SIMPLE: app-layer tenant filtering violates security brief; FR-only i18n creates later rework
- 🟡 BALANCED: RLS is weaker than schema isolation for critical infrastructure; no ML anomaly detection

**Key architectural choices this unlocks**:
- Backend: FastAPI monolith, layered architecture (routers → services → repos)
- DB: PostgreSQL + TimescaleDB + PostGIS, schema-per-tenant
- Queue: Celery + Redis
- Storage: MinIO (S3-compatible)
- ML: Isolation Forest (sklearn) + z-score anomaly detection
- Frontend: React + Vite + TypeScript + Tailwind + i18next (FR/AR RTL)
- Security: STRIDE + adversarial review + OWASP ZAP DAST + Law 09-08
- Ops: Docker Compose (7 services) + GitHub Actions CI/CD
- Repo: https://github.com/rhorba/tanqitflow

**Sprint count**: 10 sprints × 2 weeks = 20 weeks

---
