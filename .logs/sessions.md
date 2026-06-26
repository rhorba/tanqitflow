# Sessions Log — TanqitFlow

---

## SESSION_START — 2026-06-26 (Sprint 10)

**Project**: TanqitFlow — Sprint 10 Production Hardening & Ship
**Resumed from**: Sprint 9 complete (commit 914cb7c, 81.73% coverage)
**Phase**: EXECUTE → VERIFY → SHIP (Sprint 10, all 5 stories)

---

## SESSION_END — 2026-06-26 (Sprint 10)

**Phases completed**: UNDERSTAND → BRAINSTORM → PLAN → EXECUTE (Sprint 10) → VERIFY → SHIP

**What was done**:
- Story 10.1: Prod compose hardened — api healthcheck, `driver: local` on all volumes, REDIS_PASSWORD in .env.example, SMTP defaults
- Story 10.2: GitHub Actions CI/CD — pr.yml (PR validation) + deploy.yml (full: lint+test → Semgrep SAST → build+push GHCR → ZAP DAST → SSH deploy + GitHub Deployment status); frontend Dockerfile.prod (multi-stage nginx build)
- Story 10.3: OpenAPI docs enabled in production, gated by DocsAuthMiddleware (utility_admin JWT); all endpoints have summary + description; openapi_tags metadata; nginx passes /docs through to FastAPI; title = "TanqitFlow API v1.0"
- Story 10.4: docs/deployment-guide.md — full VPS guide (provision, secrets, TLS, migrations, pilot tenant, smoke tests, CI/CD, monitoring, backups, troubleshooting)
- Story 10.5: v1-recording.spec.ts (9 critical flows), scripts/record-v1.sh, .recordings/ dir; git tag v1.0 pushed
- VERIFY: ruff clean, AST valid, frontend lint pass, 81.73% coverage (held from Sprint 9)
- SHIP: commit + push + git tag v1.0

**GitHub Secrets required** (user must add before pipeline can deploy):
  - VPS_HOST, VPS_USER, VPS_SSH_KEY, VPS_DEPLOY_PATH

**Recording**: Run `scripts/record-v1.sh` once VPS is live to capture .recordings/v1.0-[date]-full.webm

**GitHub**: https://github.com/rhorba/tanqitflow
**Tag**: v1.0
**Status**: ALL 10 SPRINTS COMPLETE — TanqitFlow v1.0 shipped 🎉

---

## SESSION_START — 2026-06-26

**Project**: TanqitFlow — NRW Intelligence Platform
**Resumed from**: Sprint 5 leak detection (after Sprint 5.1 PostGIS map commit ef79dd1)
**Phase**: EXECUTE → VERIFY → SHIP
**Last commit**: ef79dd1 (85 tests, 82% coverage)
**Status**: Sprints 1–4 complete + PostGIS map done. Leak detection engine (5.1–5.5) not yet implemented.

---

## SESSION_END — 2026-06-26 (Sprint 5)

**Phases completed this session**: UNDERSTAND → BRAINSTORM (🔴 COMPREHENSIVE) → PLAN → EXECUTE (Sprint 5) → VERIFY → SHIP

**What was done**:
- BATCH 1 — DB models + migrations:
  - Alembic 0006: leak_indicator, anomaly_event (TimescaleDB hypertable), worklist_item
  - ORM models: LeakIndicator, AnomalyEvent, WorklistItem (all tenant-schema)
  - Pydantic schemas: LeakIndicatorOut, AnomalyEventOut, WorklistItemOut, WorklistStatusPatch
  - Tenant DDL (provision_tenant): 3 new tables + indexes added
- BATCH 2 — Pure domain logic:
  - mnf_calculator.py: MNF per DMA (Africa/Casablanca TZ, rolling 30-night baseline, 1.5× threshold)
  - zscore_detector.py: rolling 30-day z-score, AnomalyPoint detection
  - isolation_forest.py: sklearn IsolationForest, per-tenant model pickle, build_feature_vector
  - confidence_score.py: weighted 3-signal combiner (MNF=0.4, Z=0.3, IF=0.3; redistributed if IF disabled)
  - worklist_ranker.py: rank_score = loss × cost × (confidence/100), filters < 10%
- BATCH 3 — Celery tasks:
  - nightly_leak_detection: runs full pipeline per DMA; 05:00 Casablanca Beat schedule
  - monthly_if_retrain: retrains IF models for all DMAs with ≥90 days; 1st-of-month schedule
- BATCH 4 — APIs:
  - GET /api/v1/leak/indicators (paginated, filter: dma_code, alert_type, flagged_only)
  - GET /api/v1/leak/anomalies (paginated, filter: dma_code, metric)
  - POST /api/v1/worklist/generate (ROI ranking + upsert)
  - GET /api/v1/worklist (paginated, filter: status)
  - PATCH /api/v1/worklist/{id} (OPEN→IN_PROGRESS→RESOLVED|DEFERRED)
  - GET /api/v1/worklist/export?format=csv (UTF-8-sig download)
- VERIFY: 119/119 tests passing, 82.35% coverage
- SHIP: commit 986fef0 pushed → github.com/rhorba/tanqitflow

**Resume from**: Sprint 6 — Dashboard & Visualization
Stories:
  6.1 Dashboard KPI cards + trend chart (date range selector, delta vs prev period)
  6.2 Sortable DMA table (click → /dma/{id} detail page)
  6.3 Worklist UI (ranked table, status updates, CSV export button)
  6.4 DMA detail page (IWA breakdown, 12-month chart, anomaly events list)

**Key architectural decisions in force**:
  - Schema-per-tenant (ADR-001)
  - All new UI strings → both fr/common.json and ar/common.json
  - All write endpoints covered by AuditLogMiddleware
  - bcrypt directly (no passlib)
  - Isolation Forest models stored in MinIO at {tenant}/models/if_model_{dma_code}.pkl

**GitHub**: https://github.com/rhorba/tanqitflow
**Last commit**: 986fef0

---

## SESSION_START — 2026-06-25

**Project**: TanqitFlow — NRW Intelligence Platform for Moroccan water utilities
**Phase**: UNDERSTAND (Phase 1 of 6)
**Workflow**: Document-First Build (PRD → Architecture → Stories → Execute)
**Status**: Awaiting user answers to 3 clarifying questions before BRAINSTORM gate
**Specialists queued**: PM → System Designer → Software Architect → Security Engineer → DBA → UX → Tech Lead → Scrum Master → devs

---

## SESSION_END — 2026-06-25

**Phases completed this session**: UNDERSTAND → BRAINSTORM → PLAN → EXECUTE (Sprint 1) → partial SHIP

**What was done**:
- UNDERSTAND: Q1/Q2/Q3 answered (hundreds of DMAs, CSV/ERP batch, Docker + GitHub CI/CD)
- BRAINSTORM: 🔴 COMPREHENSIVE chosen — schema-per-tenant, TimescaleDB, ML, ZAP DAST
- PLAN: All 4 Document-First docs written (PRD, System Design, Architecture, Stories+Backlog)
  - 10 sprints · 53 stories · ~260 SP · full acceptance criteria
- EXECUTE Sprint 1 (8 stories, ~26 SP): Docker Compose, FastAPI, Alembic, Celery, MinIO, React, i18n, CI
- PUSH: commit 41c9efe + fd2b406 → github.com/rhorba/tanqitflow (main branch)
- README: comprehensive bilingual FR/AR overview with Arabic pipeline diagram

**Resume from**: Sprint 2 — Auth + Multi-Tenant Core (7 stories, ~25 SP)
Stories:
  2.1 JWT authentication endpoints (login/refresh/logout + brute-force protection)
  2.2 RBAC dependency (require_role, 3 roles: utility_admin / analyst / field_viewer)
  2.3 TenantContextMiddleware (JWT decode → schema routing, full implementation)
  2.4 Tenant provisioning API (create schema per tenant, MinIO path prefix)
  2.5 User management within tenant (CRUD, role constraints)
  2.6 Audit logging middleware (DB persistence, append-only trigger)
  2.7 Login + password reset UI pages (FR/AR, httpOnly cookie for refresh token)

**Key architectural decisions in force**:
- Schema-per-tenant (ADR-001): every new router must use TenantContextMiddleware
- All new UI strings: add to both fr/common.json and ar/common.json
- All write endpoints: covered by AuditLogMiddleware
- No LDAP/AD — standard JWT only

**GitHub**: https://github.com/rhorba/tanqitflow
**Local path**: C:\Users\moham\OneDrive - um5.ac.ma\Desktop\compititor\tanqitflow
**Last commit**: fd2b406

---

---

---

## SESSION_START — 2026-06-25 (Sprint 2)

**Project**: TanqitFlow — Sprint 2 resume
**Phase**: EXECUTE → VERIFY → SHIP
**Status**: Resumed from SESSION_END (Sprint 1 complete)

---

## SESSION_END — 2026-06-25 (Sprint 2)

**Phases completed this session**: EXECUTE (Sprint 2) → VERIFY → SHIP

**What was done**:
- EXECUTE: All 7 stories (2.1–2.7) implemented across 6 batches
  - 2.1: JWT login/refresh/logout + brute-force (Redis, 5 attempts/15min)
  - 2.2: RBAC require_role(UserRole.utility_admin | analyst | field_viewer)
  - 2.3: TenantContextMiddleware — full JWT decode → schema ContextVar
  - 2.4: Tenant provisioning API (CREATE SCHEMA + audit_log DDL + MinIO prefix)
  - 2.5: User CRUD (list/create/get/patch/delete) within tenant
  - 2.6: AuditLogMiddleware — DB persist to tenant.audit_log (append-only rules)
  - 2.7: LoginPage + ForgotPasswordPage (FR/AR, RTL support, ProtectedRoute)
- VERIFY: 24/24 unit tests passing (security + storage)
- Bug fixed: replaced passlib with direct bcrypt (bcrypt 5.0.0 compat)
- SHIP: commit ae30201 pushed → github.com/rhorba/tanqitflow (main)

**New files created**:
  api/models/user.py, api/core/security.py, api/schemas/{auth,tenant,user}.py
  api/routers/{auth,tenants,users}.py, api/services/tenant.py
  api/alembic/versions/0002_users.py
  api/tests/unit/test_security.py, api/tests/integration/test_auth.py
  frontend/src/stores/authStore.ts, frontend/src/lib/api.ts
  frontend/src/pages/{LoginPage,ForgotPasswordPage}.tsx
  frontend/src/components/auth/ProtectedRoute.tsx

**Resume from**: Sprint 3 — DMA Data Model + Ingestion Pipeline (7 stories, ~25 SP)
Stories:
  3.1 DMA model + migration (tenant schema: dma, geometry, metadata)
  3.2 DMA CRUD API (list/create/get/patch, analyst+)
  3.3 CSV ingestion endpoint (upload → MinIO → Celery task)
  3.4 Celery task: parse + validate DMA inflow CSV
  3.5 Celery task: parse + validate customer reads CSV
  3.6 Ingestion status API (task state from Redis/Celery result backend)
  3.7 Ingestion history UI (upload dropzone FR/AR + status table)

**Key architectural decisions in force**:
  - Schema-per-tenant (ADR-001)
  - All new UI strings → both fr/common.json and ar/common.json
  - All write endpoints covered by AuditLogMiddleware
  - Tenant data (DMA, readings) goes in tenant schema, public.users stays in public
  - bcrypt directly (no passlib) — keep this in Sprint 3+

**GitHub**: https://github.com/rhorba/tanqitflow
**Last commit**: ae30201

---

---

## SESSION_END — 2026-06-25 (Sprint 2 fix + Sprint 3)

**What was done**:
- CI FIX (8f74ca9): ruff --fix 51 errors (UP035/007/017, I001, F401) + added typescript-eslint to devDeps
- SPRINT 3 (28295aa): DMA data model + CSV ingestion pipeline
  - 3.1: DMA ORM model (TenantBase, no schema prefix — uses search_path)
  - 3.2: DMA CRUD: GET (paginated, zone filter), POST, PATCH
  - 3.3: POST /api/v1/ingestion/upload (multipart, 50MB guard, MinIO, Celery enqueue)
  - 3.4: Celery task process_dma_inflow (validate cols, upsert dma_inflow rows)
  - 3.5: Celery task process_customer_reads (validate cols, upsert customer_reads rows)
  - 3.6: GET /api/v1/ingestion/jobs + /jobs/{id} (status polling, pagination)
  - 3.7: IngestionPage (drag-and-drop dropzone, live 5s poll, status table FR/AR)
- Tenant provisioning DDL updated with dma, dma_inflow, customer_reads tables
- Migration 0003: public.ingestion_jobs table
- 24/24 tests passing, ruff clean, frontend lint + build clean

**Resume from**: Sprint 4 — NRW Balance Calculation (6 stories, ~22 SP)
Stories:
  4.1 Water balance model + migration (balance_period table in tenant schema)
  4.2 Balance calculation service (SIV - SCV = NRW, ILI, leakage index)
  4.3 Celery task: nightly balance computation
  4.4 Balance API (GET periods, GET detail with component breakdown)
  4.5 Dashboard KPI cards (SIV, NRW m³, NRW %, flagged DMAs)
  4.6 NRW trend chart (Recharts, 12-month sparkline, FR/AR)

**Last commits**: 8f74ca9 (CI fix), 28295aa (Sprint 3)
**GitHub**: https://github.com/rhorba/tanqitflow
