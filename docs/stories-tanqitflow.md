# Epics, Stories & Sprint Backlog — TanqitFlow v1.0

**Status**: APPROVED  
**Date**: 2026-06-25  
**Specialist**: Scrum Master + Test Architect  
**Total sprints**: 10 × 2 weeks = 20 weeks  
**Architecture**: 🔴 COMPREHENSIVE — Enterprise Hardened  
**Story point scale**: XS=1 · S=2 · M=3 · L=5 · XL=8

---

## Epic Map

| Epic | Sprints | Theme |
|------|---------|-------|
| E1: Foundation & Infrastructure | 1 | Scaffold, Docker, CI/CD, DB |
| E2: Auth + Multi-Tenant Core | 2 | JWT, RBAC, Schema-per-tenant, Audit |
| E3: Data Ingestion Pipeline | 3 | CSV upload, MinIO, Celery, Parsers |
| E4: Water Balance Engine | 4 | IWA algorithm, API, Compute trigger |
| E5: Leak Detection & Prioritization | 5 | MNF, Z-score, Isolation Forest, Worklist |
| E6: Dashboard & Visualization | 6 | KPIs, Charts, Map, Worklist UI |
| E7: Bilingual UI (FR/AR + RTL) | 7 | i18next, RTL, PDF reports |
| E8: Security Hardening | 8 | STRIDE, Law 09-08, Nginx, ZAP DAST |
| E9: Testing & Quality Gate | 9 | Unit, Integration, E2E, Load, ≥80% |
| E10: Production Hardening & Ship | 10 | Prod Compose, Full CI/CD, Deploy, v1.0 |

---

## Sprint 1 — Foundation & Infrastructure
**Duration**: Weeks 1–2  
**Goal**: A fully running Docker Compose environment with all 8 services, skeleton API, React app with RTL enabled, and GitHub CI passing.

---

### Story 1.1 — Docker Compose scaffold (all services) `L`
**As a developer**, I want a `docker-compose.dev.yml` that starts all 8 services so that the team has a consistent local environment from day one.

**Acceptance Criteria**:
- [ ] `docker compose -f docker-compose.dev.yml up --build` starts: nginx, frontend, api, worker, beat, db (TimescaleDB), redis, minio
- [ ] All services have healthchecks defined; `docker compose ps` shows all healthy within 60s
- [ ] Named volumes for db, redis, minio data (no bind-mounts for service data)
- [ ] `.env.example` lists all required variables; `.env` is gitignored
- [ ] `docker-compose.prod.yml` stub exists (Nginx SSL + resource limits, fully fleshed out in Sprint 10)

---

### Story 1.2 — PostgreSQL + TimescaleDB + PostGIS initial setup `M`
**As a DBA**, I want the database initialized with TimescaleDB + PostGIS extensions, a `public.tenants` table, and an Alembic migration framework configured for multi-schema operation.

**Acceptance Criteria**:
- [ ] `timescaledb` and `postgis` extensions created on startup via init SQL
- [ ] `public.tenants` table created by Alembic migration `0001_initial`
- [ ] Alembic configured to run migrations per-tenant schema (env.py handles dynamic schema list)
- [ ] `alembic upgrade head` runs without error against the Docker DB
- [ ] Test confirms `SELECT extname FROM pg_extension` returns both `timescaledb` and `postgis`

---

### Story 1.3 — FastAPI application scaffold `M`
**As a developer**, I want a FastAPI app with layered structure, tenant middleware skeleton, and health endpoint.

**Acceptance Criteria**:
- [ ] `GET /health` returns `{ "status": "ok", "db": "ok", "redis": "ok", "minio": "ok" }`
- [ ] TenantContextMiddleware registered (no-op until Sprint 2 JWT is implemented)
- [ ] AuditLogMiddleware registered (no-op skeleton)
- [ ] OpenAPI docs accessible at `/docs` and `/redoc`
- [ ] Pydantic Settings loads all config from env vars (no hardcoded values anywhere)
- [ ] `ruff` linting passes with 0 errors

---

### Story 1.4 — Celery + Redis worker setup `S`
**As a developer**, I want Celery workers and Celery Beat configured as separate Docker services.

**Acceptance Criteria**:
- [ ] `worker` service starts Celery with `--concurrency=4`
- [ ] `beat` service starts Celery Beat with a persistent schedule store (DB scheduler)
- [ ] A smoke task `ping_task` exists; POST `/debug/ping` dispatches it; result visible in logs within 5s
- [ ] Redis broker connection confirmed (worker logs show "Connected to redis://redis:6379/0")

---

### Story 1.5 — MinIO setup + upload utility `S`
**As a developer**, I want MinIO running in Docker with a `tanqitflow-uploads` bucket and a tested upload utility.

**Acceptance Criteria**:
- [ ] MinIO accessible at `http://minio:9000` (internal); console at port 9001
- [ ] Bucket `tanqitflow-uploads` created on first startup (init script or lifecycle policy)
- [ ] `storage.py` utility: `upload_file(bucket, key, data) → str`, `download_file(bucket, key) → bytes`, `get_presigned_url(bucket, key, expires_in) → str`
- [ ] Unit test: upload → download round-trip passes

---

### Story 1.6 — React + Vite + TypeScript scaffold with i18n + RTL `L`
**As a developer**, I want the React app scaffolded with i18next (FR/AR) and Tailwind RTL support from day one.

**Acceptance Criteria**:
- [ ] `npm run dev` starts on port 3000; `npm run build` produces dist/ with 0 TypeScript errors
- [ ] i18next configured with `fr` and `ar` namespaces; `common.json` for both languages
- [ ] Language switcher component toggles between FR and AR; persists to localStorage
- [ ] `<html dir="rtl">` set when AR active; `dir="ltr"` for FR
- [ ] Tailwind `tailwindcss-rtl` plugin applied; a test component verifies mirrored flex layout
- [ ] `eslint` passes with 0 errors

---

### Story 1.7 — GitHub Actions CI pipeline `M`
**As a DevOps engineer**, I want a GitHub Actions workflow that runs on every push to any branch.

**Acceptance Criteria**:
- [ ] Workflow file: `.github/workflows/ci.yml`
- [ ] Jobs: `lint-backend` (ruff) → `test-backend` (pytest, fails if coverage < 80%) → `lint-frontend` (eslint) → `build-frontend` (vite build)
- [ ] All jobs must pass before merge to `main` (branch protection rule configured in repo)
- [ ] Pytest runs against a test Postgres + Redis launched as GitHub Actions services
- [ ] CI badge visible in README

---

### Story 1.8 — Git repo initialization + first push `XS`
**As a developer**, I want the repo initialized with `.gitignore`, `README.md`, and pushed to `github.com/rhorba/tanqitflow`.

**Acceptance Criteria**:
- [ ] `.gitignore` covers: `.env`, `__pycache__`, `*.pyc`, `node_modules`, `dist/`, `.venv/`, `*.webm`
- [ ] `README.md` contains: project name, description, quickstart (`docker compose up`), CI badge
- [ ] Initial commit pushed to `main` branch on `github.com/rhorba/tanqitflow`
- [ ] GitHub repo has branch protection on `main` (require CI pass before merge)

**Sprint 1 total**: ~26 SP | Est: 2 weeks

---

## Sprint 2 — Auth + Multi-Tenant Core
**Duration**: Weeks 3–4  
**Goal**: Full JWT auth with RBAC, schema-per-tenant provisioning, audit logging, and auth UI pages.

---

### Story 2.1 — JWT authentication endpoints `L`
**As a user**, I want to log in and receive JWT tokens for API access.

**Acceptance Criteria**:
- [ ] `POST /auth/login` accepts `{ email, password }` → returns `{ access_token, refresh_token, expires_in }`
- [ ] Access token TTL: 15 minutes; refresh token TTL: 7 days
- [ ] `POST /auth/refresh` validates refresh token → rotates (old token invalidated in Redis)
- [ ] `POST /auth/logout` adds refresh token to Redis blacklist
- [ ] Brute force: 5 failed logins in 15 min → account locked for 15 min (Redis counter)
- [ ] Password hashed with bcrypt (cost factor 12)
- [ ] JWT payload: `{ sub: user_id, tenant: tenant_slug, role, exp }`

---

### Story 2.2 — RBAC dependency + role enforcement `M`
**As a developer**, I want a reusable FastAPI dependency that enforces role-based access.

**Acceptance Criteria**:
- [ ] `require_role(["utility_admin", "analyst"])` dependency raises 403 if caller's role not in list
- [ ] All routers from Sprint 3+ use this dependency; no unprotected endpoint except /health and /auth/*
- [ ] Integration test: analyst calling admin endpoint → 403; field_viewer calling analyst endpoint → 403
- [ ] Role hierarchy: utility_admin > analyst > field_viewer (no role can grant higher than own)

---

### Story 2.3 — TenantContextMiddleware (schema routing) `L`
**As a developer**, I want every DB query automatically scoped to the requesting user's tenant schema.

**Acceptance Criteria**:
- [ ] Middleware decodes JWT → extracts `tenant_slug` → sets `SET search_path TO {tenant_slug}, public` per DB session
- [ ] Requests without valid JWT (except /health, /auth/*) → 401
- [ ] Requests with JWT for non-existent tenant → 403
- [ ] Integration test: two tenants with identical DMA IDs; user A cannot see user B's data
- [ ] `search_path` reset after request (no session leakage in connection pool)

---

### Story 2.4 — Tenant provisioning API `M`
**As a platform operator**, I want to create and configure tenants via API.

**Acceptance Criteria**:
- [ ] `POST /admin/tenants` (platform-admin role only): creates DB schema, runs tenant migrations, creates MinIO path prefix
- [ ] Tenant config fields: slug, name, region, cost_conventional_mad, cost_desalinated_mad, enable_ml_detection
- [ ] `GET /admin/tenants` lists all tenants (platform-admin only)
- [ ] `PATCH /admin/tenants/{slug}` updates config
- [ ] Delete is soft (is_active=false); PII archival job queued, hard schema drop deferred 30 days

---

### Story 2.5 — User management within tenant `M`
**As a utility admin**, I want to create and manage users in my own tenant.

**Acceptance Criteria**:
- [ ] `POST /users` (utility_admin only): creates user in current tenant schema; role must be ≤ creator's role
- [ ] `GET /users` lists users in current tenant (utility_admin sees all; analyst sees none)
- [ ] `PATCH /users/{id}` updates name, role, assigned_dmas, is_active
- [ ] `DELETE /users/{id}` soft-deactivates (is_active=false); cannot delete self
- [ ] Welcome email sent via SMTP on user creation (SMTP config in env vars)

---

### Story 2.6 — Audit logging middleware `M`
**As a compliance officer**, I want all write operations logged to an append-only audit trail.

**Acceptance Criteria**:
- [ ] AuditLogMiddleware intercepts all POST/PUT/PATCH/DELETE requests
- [ ] Log entry: user_id, action (method + path), resource_type, resource_id (from response if available), ip_address, user_agent, request_body_hash, http_status, timestamp
- [ ] `GET /audit-logs` (utility_admin only) returns paginated audit log for their tenant
- [ ] DB trigger prevents UPDATE/DELETE on audit_log table (enforced at DB level)
- [ ] Unit test: 3 write operations → 3 audit entries; read operation → 0 entries

---

### Story 2.7 — Login, password reset UI pages `M`
**As a user**, I want a login page and password reset flow in the React app.

**Acceptance Criteria**:
- [ ] `/login` page: email + password form; error message on invalid credentials (generic: "Email ou mot de passe incorrect" — no enumeration)
- [ ] Redirect to dashboard on success; token stored in memory (not localStorage); refresh token in httpOnly cookie
- [ ] "Forgot password" → `POST /auth/forgot-password` → email with 1-hour token → `/reset-password?token=...` form
- [ ] Both pages fully translated FR + AR with RTL layout
- [ ] Logout clears auth state and calls `POST /auth/logout`

**Sprint 2 total**: ~25 SP | Est: 2 weeks

---

## Sprint 3 — Data Ingestion Pipeline
**Duration**: Weeks 5–6  
**Goal**: CSV upload → MinIO storage → Celery async processing → TimescaleDB bulk insert, with configurable column mapping and row-level error reporting.

---

### Story 3.1 — CSV upload API + job management `L`
**As an analyst**, I want to upload a CSV file and track its processing progress.

**Acceptance Criteria**:
- [ ] `POST /ingestion/upload` accepts `multipart/form-data`: file (max 50 MB) + file_type (`DMA_INFLOW|CUSTOMER_READS|PRESSURE_FLOW`)
- [ ] File stored in MinIO at `{tenant}/{year}/{month}/raw/{uuid}_{filename}` immediately
- [ ] `IngestionJob` record created (status=QUEUED, sha256 of file stored)
- [ ] Celery task `csv_ingest_task(job_id)` dispatched; returns `{ job_id }` to client
- [ ] `GET /ingestion/jobs/{id}` returns: status, progress_pct, rows_processed, error_count, errors (first 100)
- [ ] `GET /ingestion/jobs` lists all jobs for tenant (paginated, sortable by created_at)

---

### Story 3.2 — Tenant column mapping configuration `M`
**As a utility admin**, I want to define which columns in my ERP export correspond to TanqitFlow's expected fields.

**Acceptance Criteria**:
- [ ] `GET /ingestion/mappings/{file_type}` returns current mapping for tenant (default if not configured)
- [ ] `PUT /ingestion/mappings/{file_type}` saves custom column mapping: `{ "dma_id_column": "CODE_UDI", "timestamp_column": "DATE_RELEVE", ... }`
- [ ] Default mappings ship with the system (standard ONEE ERP column names)
- [ ] Column mapping applied at parse time in Celery task

---

### Story 3.3 — DMA inflow meter CSV parser `L`
**As the system**, I want to parse and store DMA inflow meter readings from CSV.

**Acceptance Criteria**:
- [ ] Parser handles: dma_id, timestamp (ISO 8601 or `DD/MM/YYYY HH:MM`), flow_m3, pressure_bar
- [ ] Validates: dma_id exists in tenant, timestamp valid, flow_m3 ≥ 0, pressure_bar ≥ 0
- [ ] Bulk inserts into `dma_reading` hypertable using `asyncpg COPY` (100K rows < 60s)
- [ ] Duplicate (dma_id, time) → upsert (last-write-wins)
- [ ] Error rows collected in `errors_json`; processing continues on non-fatal errors
- [ ] Unit tests: valid file, file with 10% invalid rows, empty file, wrong encoding

---

### Story 3.4 — Customer meter reads CSV parser `L`
**As the system**, I want to parse and store customer meter reads from ERP CSV.

**Acceptance Criteria**:
- [ ] Parser handles: meter_id, dma_id, read_date, read_m3, customer_ref (optional PII)
- [ ] Computes `consumption_m3 = current_read - previous_read` per meter
- [ ] Flags negative consumption (meter rollover or reading error) as `is_estimated=true`
- [ ] `customer_ref` encrypted with AES-256 before insert (pgcrypto)
- [ ] Bulk insert to `meter_read` table; duplicate (meter_id, read_date) → upsert
- [ ] Unit tests: standard file, meter rollover detection, missing previous read

---

### Story 3.5 — SCADA pressure/flow CSV parser `M`
**As the system**, I want to parse and store SCADA pressure and flow time-series from CSV.

**Acceptance Criteria**:
- [ ] Shares dma_reading hypertable with DMA_INFLOW type (same schema)
- [ ] Handles higher-frequency data (15-min or hourly intervals)
- [ ] Detects and skips duplicate rows (same dma_id + timestamp already in DB)
- [ ] Unit tests: 15-min interval file, hourly interval file, mixed frequency

---

### Story 3.6 — Ingestion history UI `M`
**As an analyst**, I want to see all past ingestion jobs in the React app.

**Acceptance Criteria**:
- [ ] `/ingestion` page: table with filename, type, uploaded_by, uploaded_at, status badge, rows_processed, error_count
- [ ] Status badge: QUEUED (grey) / PROCESSING (blue spinner) / DONE (green) / ERROR (red)
- [ ] Polling: auto-refresh every 5s for jobs in QUEUED/PROCESSING state
- [ ] Click job → modal with full error list (row_number, column, message)
- [ ] "Re-download original" button → presigned MinIO URL → browser download
- [ ] File upload dropzone with drag-and-drop + progress bar

**Sprint 3 total**: ~28 SP | Est: 2 weeks

---

## Sprint 4 — Water Balance Engine
**Duration**: Weeks 7–8  
**Goal**: Full IWA water balance algorithm, per-DMA and per-region computation, historical trend data, API endpoints.

---

### Story 4.1 — IWA water balance domain service `XL`
**As the system**, I want a pure Python IWA water balance calculator.

**Acceptance Criteria**:
- [ ] `iwa_engine.py` accepts: `siv_m3`, `bac_m3`, `uac_m3`, `al_metering_pct`, `al_theft_pct`, `cost_per_m3` → returns `WaterBalance` dataclass with all IWA components
- [ ] Components computed: SIV, BAC, UAC, AL_metering, AL_theft, RL = SIV - BAC - UAC - AL_metering - AL_theft, NRW = SIV - BAC, NRW% = (NRW/SIV)×100, NRW_MAD = NRW × cost_per_m3
- [ ] Edge cases: SIV = 0 → NRW% = None (not divide-by-zero); negative RL capped at 0 with warning flag
- [ ] No I/O; no DB imports; fully unit-testable
- [ ] 100% unit test coverage on this module (enforced)
- [ ] Unit tests: standard case, zero SIV, RL goes negative, high apparent losses

---

### Story 4.2 — Water balance computation service + Celery task `L`
**As the system**, I want to trigger water balance computation for a set of DMAs and a billing period.

**Acceptance Criteria**:
- [ ] `BalanceService.compute(dma_ids, period_start, period_end)`: queries dma_reading + meter_read → calls iwa_engine → stores in water_balance table
- [ ] `POST /balance/compute` dispatches Celery `water_balance_task(dma_ids, period)` → returns job_id
- [ ] Task runs per DMA; progress_pct updated per completed DMA
- [ ] Automatically triggered by `csv_ingest_task` on completion (fan-out)
- [ ] Upserts results (recompute if same period exists)
- [ ] Integration test: upload DMA_INFLOW + CUSTOMER_READS → trigger compute → assert NRW% row exists

---

### Story 4.3 — Water cost configuration `S`
**As a utility admin**, I want to configure water cost per m³ for my tenant.

**Acceptance Criteria**:
- [ ] `PATCH /admin/tenant-config` accepts: `cost_conventional_mad`, `cost_desalinated_mad`
- [ ] Defaults: 4.0 and 16.0 MAD/m³
- [ ] Used by IWA engine when computing NRW_MAD
- [ ] Changing cost config triggers recompute of all historical balances (async Celery task)

---

### Story 4.4 — Water balance API endpoints `M`
**As an analyst**, I want to query water balance results via API.

**Acceptance Criteria**:
- [ ] `GET /balance?dma_id=&from=&to=` returns list of WaterBalance records with all IWA components
- [ ] `GET /balance/region?from=&to=` returns aggregated totals across all DMAs in tenant
- [ ] `GET /balance/trend?dma_id=&periods=12` returns last N period NRW% values (for trend chart)
- [ ] Response times: < 300ms for single DMA; < 500ms for 300 DMAs region aggregate (TimescaleDB)
- [ ] field_viewer can only query their assigned_dmas

---

### Story 4.5 — DMA management API `M`
**As a utility admin**, I want to register and manage DMAs in my tenant.

**Acceptance Criteria**:
- [ ] `POST /dmas` creates DMA: code, name, name_ar, polygon (GeoJSON optional), area_km2
- [ ] `GET /dmas` lists all DMAs in tenant (paginated)
- [ ] `PATCH /dmas/{id}` updates name, polygon, area_km2
- [ ] `POST /dmas/upload-boundaries` accepts GeoJSON FeatureCollection → bulk upserts polygons from properties.code
- [ ] If no polygon: DMA still functional (map shows list instead of polygon)

**Sprint 4 total**: ~24 SP | Est: 2 weeks

---

## Sprint 5 — Leak Detection & Prioritization
**Duration**: Weeks 9–10  
**Goal**: MNF analysis, z-score anomaly detection, Isolation Forest ML scoring, combined confidence score, ranked repair worklist.

---

### Story 5.1 — Minimum Night Flow (MNF) analysis `L`
**As the system**, I want to compute MNF per DMA and flag anomalies.

**Acceptance Criteria**:
- [ ] `mnf_calculator.py` (pure Python): given a DataFrame of hourly flow readings, returns `{ dma_id, date, mnf_m3h, baseline_m3h, mnf_flag }`
- [ ] MNF = min flow between 02:00–04:00 local time (Africa/Casablanca TZ)
- [ ] Baseline = rolling median of last 30 nights (min 7 nights required)
- [ ] Flag condition: `mnf > baseline × threshold` (default 1.5×, configurable per tenant)
- [ ] Nightly Celery Beat task: `nightly_mnf_task` runs at 05:00 Casablanca time
- [ ] Results stored in `leak_indicator` table (upsert by dma_id + date)
- [ ] Unit tests: steady flow (no flag), sudden spike, insufficient history (< 7 nights)

---

### Story 5.2 — Z-score anomaly detection `M`
**As the system**, I want to detect statistical anomalies in flow and pressure time-series.

**Acceptance Criteria**:
- [ ] `zscore_detector.py` (pure Python): rolling 30-day z-score per DMA metric
- [ ] Flag: |z| > 3.0 (configurable threshold)
- [ ] Stores flagged points in `anomaly_event` hypertable
- [ ] Runs as part of `leak_detection_task` after each water balance compute
- [ ] Returns max |z| per DMA per week (for confidence score)
- [ ] Unit tests: stationary series (no flags), injected spike, sparse data handling

---

### Story 5.3 — Isolation Forest ML anomaly detection `XL`
**As the system**, I want an ML-based anomaly detector for subtle multi-variate patterns in flow + pressure.

**Acceptance Criteria**:
- [ ] `isolation_forest.py` (pure Python + sklearn): trains on features per DMA: `[hourly_mean_flow, hourly_std_flow, mnf_m3h, daily_range_flow, night_day_ratio, mean_pressure, std_pressure]`
- [ ] Requires ≥ 90 days of data; if insufficient → returns `{ score: None, reason: "insufficient_data" }`
- [ ] Anomaly score (0–1, higher = more anomalous) stored in `leak_indicator.if_anomaly_score`
- [ ] Per-tenant model stored as pickle in MinIO at `{tenant}/models/if_model_{dma_id}.pkl`
- [ ] Monthly retrain job (`monthly_retrain_task` via Celery Beat) retrains all DMA models
- [ ] Feature: `enable_ml_detection` tenant flag must be True (default False for new tenants)
- [ ] Unit tests: normal data → low score; injected anomalies → high score; missing columns handled

---

### Story 5.4 — Combined confidence score `M`
**As the system**, I want a single 0–100 confidence score per DMA combining all three leak signals.

**Acceptance Criteria**:
- [ ] `confidence_score = weighted_average(mnf_contribution, zscore_contribution, if_contribution)`
- [ ] Weights (configurable in tenant config): mnf=0.4, zscore=0.3, if=0.3
- [ ] If IF disabled: weights redistibuted to mnf=0.6, zscore=0.4
- [ ] Score stored in `leak_indicator.confidence_score` (0–100 INTEGER)
- [ ] `alert_type` field: `MNF` | `ZSCORE` | `ISOLATION_FOREST` | `COMBINED` based on which signals fired
- [ ] Unit tests: all signals fire (combined), only MNF fires, no data (score=0)

---

### Story 5.5 — Repair worklist generation + API `L`
**As an analyst**, I want a ranked repair worklist showing which DMAs to fix first for maximum water saved per dirham.

**Acceptance Criteria**:
- [ ] `worklist_ranker.py` (pure Python): `rank_score = estimated_loss_m3_per_month × water_cost × (confidence / 100)`
- [ ] `POST /worklist/generate` dispatches `worklist_generate_task` → upserts `worklist_item` table for all DMAs with confidence > 10
- [ ] `GET /worklist` returns ranked list: rank, dma_id, dma_name, loss_m3_est, savings_mad_est, confidence, alert_type, status
- [ ] `PATCH /worklist/{id}` updates status: `OPEN → IN_PROGRESS → RESOLVED | DEFERRED`
- [ ] Status update requires analyst or utility_admin role
- [ ] `GET /worklist/export?format=csv` → CSV download; `format=pdf` → dispatches pdf_report_task
- [ ] Auto-generates after each `leak_detection_task` completes

---

**Sprint 5 total**: ~27 SP | Est: 2 weeks

---

## Sprint 6 — Dashboard & Visualization
**Duration**: Weeks 11–12  
**Goal**: Full interactive dashboard: KPI cards, NRW% trend chart, sortable DMA table, PostGIS hotspot map, repair worklist UI.

---

### Story 6.1 — Dashboard KPI cards + trend chart `L`
**As an analyst**, I want a dashboard overview with key metrics and trend visualization.

**Acceptance Criteria**:
- [ ] `/dashboard` page: 4 KPI cards — Total SIV m³, Total NRW m³, NRW%, Flagged DMAs count
- [ ] NRW% trend line (Recharts LineChart) for the last 12 periods
- [ ] Date range selector: 1M / 3M / 6M / 12M quick buttons + custom date picker
- [ ] KPI cards show delta vs previous period (▲ red if worse, ▼ green if better)
- [ ] Loading skeleton shown while data fetches; error state with retry
- [ ] TanStack Query cache: 60s stale time (reduces redundant API calls)
- [ ] Loads within 3 seconds on 300-DMA tenant (measured in Playwright performance assertion)

---

### Story 6.2 — Sortable DMA table `M`
**As an analyst**, I want a table of all DMAs sortable by any column.

**Acceptance Criteria**:
- [ ] Columns: DMA Code, DMA Name, SIV m³, BAC m³, NRW m³, NRW%, Trend (7-day arrow), Leak Flag, Confidence
- [ ] Client-side sort on all columns; server-side pagination (50 per page)
- [ ] Leak flag: red warning icon if any leak_indicator.mnf_flag or zscore_flag is true
- [ ] Click row → navigate to `/dma/{id}` detail page
- [ ] DMA detail page: full IWA breakdown table, 12-month NRW% trend chart, anomaly events list, latest confidence score

---

### Story 6.3 — Hotspot map (PostGIS + Leaflet) `XL`
**As an analyst**, I want a map showing DMA boundaries color-coded by NRW% severity.

**Acceptance Criteria**:
- [ ] `GET /dashboard/geojson` returns GeoJSON FeatureCollection with all DMA polygons + properties (NRW%, confidence, alert_type)
- [ ] Leaflet map renders polygons; color scale: 0–10% green → 10–20% yellow → 20–30% orange → 30%+ red
- [ ] Click polygon → popup with: DMA name, NRW%, SIV, Savings MAD/month, Confidence%
- [ ] Three layer toggles: "NRW%", "Leak confidence", "Pressure anomalies"
- [ ] DMAs without PostGIS polygon → not shown on map (degrade gracefully; still in table)
- [ ] Map initializes centered on Morocco (lat 31.79, lng -7.09, zoom 6)
- [ ] Map loads within 2 seconds for 300 polygon features (GeoJSON response < 500KB with simplification)
- [ ] field_viewer sees only their assigned DMAs

---

### Story 6.4 — Repair worklist UI `M`
**As an analyst**, I want to review and manage the repair worklist in the UI.

**Acceptance Criteria**:
- [ ] `/worklist` page: table with Rank, DMA, Estimated Savings MAD/month, Confidence %, Alert Type, Status
- [ ] Inline status update dropdown (OPEN / IN_PROGRESS / RESOLVED / DEFERRED) — saves on change
- [ ] "Generate worklist" button triggers `POST /worklist/generate` with progress toast
- [ ] "Export CSV" and "Export PDF" buttons (PDF dispatched async, download link shown when ready)
- [ ] Rows sorted by rank; filterable by status and alert_type
- [ ] Fully translated FR + AR

---

**Sprint 6 total**: ~25 SP | Est: 2 weeks

---

## Sprint 7 — Bilingual UI (FR/AR + RTL)
**Duration**: Weeks 13–14  
**Goal**: 100% UI translation FR + AR with RTL layout, bilingual PDF reports, language-persisted per user.

---

### Story 7.1 — Complete French translations `M`
**As a French-speaking user**, I want every UI string in French with no English fallbacks.

**Acceptance Criteria**:
- [ ] All pages/components audited: 0 hardcoded English strings in JSX
- [ ] `fr/*.json` translation files complete for: common, auth, dashboard, ingestion, balance, detection, worklist, admin, reports
- [ ] Missing translation key → logs warning in dev; shows key in red in dev, empty in prod (not crashes)
- [ ] Number formatting: French locale (1 234 567,89)
- [ ] Date formatting: DD/MM/YYYY

---

### Story 7.2 — Complete Arabic translations + RTL layout `XL`
**As an Arabic-speaking user**, I want the entire UI in Arabic with proper RTL mirroring.

**Acceptance Criteria**:
- [ ] `ar/*.json` translation files complete (all namespaces)
- [ ] `dir="rtl"` on `<html>` when Arabic active
- [ ] Navigation sidebar: text right-aligned, icons on right side
- [ ] All flex layouts mirror (flex-row-reverse applied via Tailwind RTL plugin)
- [ ] Form inputs: text-right, label alignment correct
- [ ] Table: columns in same logical order; text right-aligned
- [ ] Recharts: axis labels in Arabic numerals; chart itself LTR (standard for data viz)
- [ ] Leaflet map: popup text in Arabic; attribution stays LTR
- [ ] Icons with implied direction (back arrow, chevron) flip in RTL
- [ ] Mobile: menu opens from right side in RTL

---

### Story 7.3 — Bilingual PDF report generation `L`
**As an analyst**, I want water balance reports exported as PDF in French or Arabic.

**Acceptance Criteria**:
- [ ] `pdf_report_task` generates report using WeasyPrint (HTML → PDF, supports Arabic/RTL)
- [ ] Report content: tenant name, period, DMA summary table (top 10), NRW% chart (embedded PNG via matplotlib), repair worklist
- [ ] Arabic PDF: correct RTL text direction, Arabic numerals, proper font (Amiri or Cairo)
- [ ] French PDF: standard LTR layout
- [ ] `GET /reports/water-balance?format=pdf&lang=ar&from=&to=` → dispatches task → returns `{ task_id }`
- [ ] `GET /reports/download/{task_id}` → redirects to MinIO presigned URL when ready (polling or async)
- [ ] File stored in MinIO at `{tenant}/reports/{uuid}.pdf`

---

### Story 7.4 — Language switcher + persistence `S`
**As a user**, I want my language preference saved between sessions.

**Acceptance Criteria**:
- [ ] Language switcher in Header: `FR | ع` toggle
- [ ] Selected language saved to `localStorage`
- [ ] On login, user's preferred language loaded from DB (user.language_pref column)
- [ ] `PATCH /users/me` accepts `{ language_pref: "fr" | "ar" }`
- [ ] Page title (`<title>`) also translated

**Sprint 7 total**: ~24 SP | Est: 2 weeks

---

## Sprint 8 — Security Hardening
**Duration**: Weeks 15–16  
**Goal**: STRIDE fully implemented, Law 09-08 compliance, Nginx + SSL in prod, OWASP ZAP DAST passing with 0 High findings, adversarial review checklist complete.

---

### Story 8.1 — STRIDE threat model + mitigations `XL`
**As a security engineer**, I want STRIDE analysis on all risk tier 13–15 components with every Medium+ threat mitigated.

**Acceptance Criteria**:
- [ ] `docs/threat-model.md` documents STRIDE for: Auth, Tenant Isolation, Data Ingestion API, Water Balance API, Worklist, PDF Generation
- [ ] Each threat: description, likelihood (H/M/L), impact (H/M/L), mitigation (code or config), status (MITIGATED / ACCEPTED)
- [ ] 0 High-impact threats with status ACCEPTED
- [ ] Specific mitigations implemented:
  - JWT secret rotation procedure documented
  - Tenant schema isolation verified with adversarial test (Story 8.5)
  - CSV injection prevented (formula injection in cell values stripped)
  - File upload: MIME type validation (not just extension)
  - PDF: WeasyPrint sandbox (no JS execution)
  - SQL: all queries parameterized (no string interpolation); confirmed via code review

---

### Story 8.2 — Law 09-08 PII encryption + register `L`
**As a compliance officer**, I want PII handled per Moroccan Law 09-08.

**Acceptance Criteria**:
- [ ] PII fields encrypted: `meter_read.customer_ref`, `users.full_name`, `users.email` — AES-256-CBC via pgcrypto
- [ ] Encryption key stored in env var `PII_ENCRYPTION_KEY` (never in code or DB)
- [ ] `docs/data-processing-register.md` lists: data categories, purpose, legal basis, retention, data subjects, processor details
- [ ] `docs/cndp-registration-template.md` filled with project-specific details (CNDP = Commission Nationale de Contrôle de la Protection des Données à Caractère Personnel)
- [ ] Data erasure endpoint: `DELETE /users/{id}/pii` → sets encrypted fields to NULL (keeps audit trail)
- [ ] Retention job: Celery Beat monthly task archives records older than 5 years (moves to cold storage, does not delete immediately)

---

### Story 8.3 — Nginx reverse proxy + SSL in production Compose `M`
**As an ops engineer**, I want Nginx in front of the API for production Docker Compose.

**Acceptance Criteria**:
- [ ] `docker-compose.prod.yml`: nginx service on ports 80 + 443; api/frontend not on public ports
- [ ] `nginx/nginx.conf`: upstream to api:8000 and frontend:3000; SSL on 443; HTTP → HTTPS redirect
- [ ] SSL: supports Let's Encrypt certbot volume mount OR custom certificate path in env vars
- [ ] Security headers in Nginx: `Strict-Transport-Security`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Content-Security-Policy` (strict), `Referrer-Policy`
- [ ] `client_max_body_size 55m` (for 50 MB CSV uploads)
- [ ] Rate limiting in Nginx: 30 req/s per IP on /api/; 5 req/s on /auth/login
- [ ] Test: `curl -I https://localhost` → 200; `curl -I http://localhost` → 301

---

### Story 8.4 — OWASP ZAP DAST in CI `L`
**As a security engineer**, I want automated DAST scanning in the GitHub Actions pipeline.

**Acceptance Criteria**:
- [ ] `.github/workflows/security.yml` job: spins up `docker-compose.prod.yml` → runs ZAP baseline scan against `https://localhost`
- [ ] ZAP config: authenticated scan (ZAP gets a JWT); scans all API endpoints from OpenAPI spec
- [ ] CI build fails if ZAP reports any High or Critical findings
- [ ] ZAP HTML report archived as GitHub Actions artifact (retained 30 days)
- [ ] 0 High findings at Sprint 8 end (Medium findings triaged in `docs/zap-triage.md`)

---

### Story 8.5 — Adversarial review: auth + tenant isolation `XL`
**As a security engineer**, I want a systematic adversarial test of auth and tenant boundaries.

**Acceptance Criteria**:
- [ ] `docs/adversarial-review.md` checklist signed off:
  - [ ] JWT with expired token → 401 (not 200 or 500)
  - [ ] JWT with tampered payload (role: "utility_admin") → 403
  - [ ] JWT from Tenant A used against Tenant B endpoint → 403
  - [ ] Direct DB query: SELECT from tenant_b schema using tenant_a credentials → blocked by search_path
  - [ ] field_viewer accessing analyst endpoint → 403
  - [ ] field_viewer accessing a DMA not in assigned_dmas → 404 (not 403, to avoid enumeration)
  - [ ] POST /admin/tenants by analyst → 403
  - [ ] Refresh token replay after logout → 401 (Redis blacklist)
  - [ ] Brute force: 6 attempts → 429 lockout response
  - [ ] CSV with formula injection (`=cmd|'/c calc'`) → stored as plain string, not executed
  - [ ] File upload with `.php` extension renamed to `.csv` → rejected (MIME type check)
  - [ ] PDF request with `../../../etc/passwd` as report parameter → 400 (parameter validation)
- [ ] Each item has: test method, expected result, actual result, PASS/FAIL
- [ ] All FAIL items resolved and retested before Sprint 9

**Sprint 8 total**: ~28 SP | Est: 2 weeks

---

## Sprint 9 — Testing & Quality Gate
**Duration**: Weeks 17–18  
**Goal**: ≥ 80% combined unit + integration coverage enforced in CI; Playwright E2E suite covering all critical flows; load test confirms 300-DMA scale; coverage report committed.

---

### Story 9.1 — Unit test suite: domain + services `L`
**As a developer**, I want comprehensive unit tests on all domain logic.

**Acceptance Criteria**:
- [ ] Test coverage ≥ 90% on all files in `api/domain/` (enforced by pytest-cov --fail-under=90 for domain)
- [ ] `test_iwa_engine.py`: standard case, zero SIV, negative RL, high apparent loss, all components sum correctly
- [ ] `test_mnf_calculator.py`: normal, spike, < 7 nights, night window edge cases (midnight)
- [ ] `test_zscore_detector.py`: stationary, spike, sparse (gaps), single-point series
- [ ] `test_isolation_forest.py`: normal data → low score, anomaly data → high score, insufficient data, feature missing
- [ ] `test_worklist_ranker.py`: ranking order correct, ties broken by confidence, zero cost edge case
- [ ] `test_csv_parsers.py`: DMA_INFLOW, CUSTOMER_READS, PRESSURE_FLOW parsers for valid, invalid, empty, wrong encoding

---

### Story 9.2 — Integration test suite: API + DB + Celery `XL`
**As a developer**, I want integration tests covering the full request-to-database pipeline.

**Acceptance Criteria**:
- [ ] Test Postgres + Redis + MinIO launched as pytest fixtures (Docker testcontainers or GitHub Services)
- [ ] `test_ingestion_api.py`: upload file → poll job → assert rows in DB → assert MinIO file exists
- [ ] `test_balance_api.py`: pre-seed DMA readings + meter reads → trigger compute → assert NRW% in DB → GET /balance returns correct values
- [ ] `test_detection_api.py`: pre-seed readings with anomaly → run detection task → assert confidence_score > 0 in leak_indicator
- [ ] `test_auth_api.py`: login → use token → refresh → logout → replay revoked token → 401
- [ ] `test_tenant_isolation.py`: create 2 tenants → tenant A uploads data → tenant B queries same endpoint → returns empty (not tenant A's data)
- [ ] Combined coverage (unit + integration) ≥ 80% enforced in CI (`pytest --cov --cov-fail-under=80`)

---

### Story 9.3 — Playwright E2E test suite `XL`
**As a tester**, I want E2E tests for all critical user flows with video recording.

**Acceptance Criteria**:
- [ ] Playwright config: `use: { video: 'on', screenshot: 'only-on-failure' }`; output to `tests/e2e/artifacts/`
- [ ] `auth.spec.ts`: login with valid creds → dashboard visible; invalid creds → error message; logout → login page
- [ ] `ingestion.spec.ts`: upload CSV → job shows PROCESSING → job shows DONE → row count visible
- [ ] `dashboard.spec.ts`: KPI cards load; trend chart renders; date range filter updates data
- [ ] `map.spec.ts`: map loads; polygon visible; click → popup with DMA name; layer toggle works
- [ ] `worklist.spec.ts`: worklist table loads; status update works; CSV export downloads
- [ ] `i18n.spec.ts`: switch to Arabic → dir="rtl" on html; key strings translated; switch back to FR → LTR
- [ ] All tests run against Docker Compose environment in CI (`docker compose up` before tests)
- [ ] Recording saved: `tests/e2e/artifacts/*.webm` archived as CI artifact

---

### Story 9.4 — Load test: 300-DMA CSV import `M`
**As a performance engineer**, I want to verify the system handles production-scale data volumes.

**Acceptance Criteria**:
- [ ] Locust or k6 load test script in `tests/load/`
- [ ] Scenario 1: single CSV import of 300K rows (300 DMAs × 1,000 customer reads) → completes within 60 seconds (Celery worker)
- [ ] Scenario 2: 50 concurrent users querying `/dashboard/summary` → P95 < 500ms
- [ ] Scenario 3: 10 concurrent CSV uploads (separate tenants) → all complete, no deadlocks
- [ ] Load test results summary documented in `docs/load-test-results.md`
- [ ] Any P95 > 500ms: add to Sprint 10 performance backlog

---

**Sprint 9 total**: ~27 SP | Est: 2 weeks

---

## Sprint 10 — Production Hardening & Ship
**Duration**: Weeks 19–20  
**Goal**: Production Docker Compose hardened, full CI/CD pipeline (test → SAST → DAST → build → deploy), first VPS deployment, Playwright recording, git tag v1.0.

---

### Story 10.1 — Production Docker Compose hardening `L`
**As a DevOps engineer**, I want a production-hardened Docker Compose.

**Acceptance Criteria**:
- [ ] `docker-compose.prod.yml`: all services have CPU/memory limits appropriate for 4vCPU/8GB VPS
  - api: 1 CPU, 1GB RAM; worker: 1 CPU, 1.5GB RAM; db: 1 CPU, 2GB RAM; redis: 0.2 CPU, 256MB; minio: 0.5 CPU, 512MB; nginx: 0.1 CPU, 128MB; frontend: 0.1 CPU, 128MB
- [ ] All services: `restart: unless-stopped`
- [ ] Healthchecks on all services with sensible intervals (db: pg_isready, redis: ping, minio: /minio/health/live)
- [ ] Named volumes with driver: local for db, redis, minio (survives `docker compose down`)
- [ ] `.env.example` lists ALL env vars with descriptions; no defaults for secrets
- [ ] `POSTGRES_PASSWORD`, `JWT_SECRET`, `PII_ENCRYPTION_KEY`, `MINIO_ROOT_PASSWORD` required — startup fails with clear error if missing

---

### Story 10.2 — Full GitHub Actions CI/CD pipeline `XL`
**As a DevOps engineer**, I want the complete pipeline from code push to VPS deployment.

**Acceptance Criteria**:
- [ ] **PR pipeline** (`.github/workflows/pr.yml`): lint-backend → lint-frontend → test-backend (coverage gate) → build-frontend
- [ ] **Main pipeline** (`.github/workflows/deploy.yml`) on push to `main`:
  1. `lint-and-test`: ruff + eslint + pytest (≥80% coverage gate)
  2. `semgrep-sast`: Semgrep with `p/python` and `p/javascript` rules; fails on critical
  3. `build-and-push`: builds Docker images → pushes `ghcr.io/rhorba/tanqitflow-api:latest` + `ghcr.io/rhorba/tanqitflow-frontend:latest`
  4. `zap-dast`: spins up Docker Compose → runs ZAP → fails on High findings
  5. `deploy`: SSH to VPS → `docker compose -f docker-compose.prod.yml pull && docker compose up -d`
- [ ] All secrets in GitHub Secrets (VPS_SSH_KEY, VPS_HOST, etc.)
- [ ] Deployment notification: GitHub deployment status API updated

---

### Story 10.3 — OpenAPI documentation `M`
**As an API consumer**, I want complete, accurate API documentation.

**Acceptance Criteria**:
- [ ] All FastAPI endpoints have `summary`, `description`, `response_model` defined
- [ ] All request schemas have field descriptions and examples
- [ ] Authentication documented: example curl with JWT flow
- [ ] `/docs` (Swagger UI) and `/redoc` (ReDoc) accessible in production (auth-gated: utility_admin only)
- [ ] API version in OpenAPI title: `TanqitFlow API v1.0`

---

### Story 10.4 — First production deployment + smoke test `L`
**As a product owner**, I want TanqitFlow deployed to a VPS and accessible to the ONEE pilot team.

**Acceptance Criteria**:
- [ ] VPS provisioned (min 4vCPU, 8GB RAM, 100GB SSD, Ubuntu 22.04)
- [ ] `docker-compose.prod.yml` deployed via CI pipeline
- [ ] HTTPS working with valid certificate (Let's Encrypt or provided cert)
- [ ] Smoke test checklist passed:
  - [ ] Login as utility_admin → dashboard loads
  - [ ] Upload sample DMA_INFLOW CSV → job completes, rows visible
  - [ ] Water balance computed → NRW% visible in dashboard
  - [ ] Map loads with at least 1 DMA polygon
  - [ ] Language switch FR ↔ AR works
  - [ ] `/health` returns 200 with all services ok
- [ ] Pilot tenant created: ONEE Casablanca; admin user provisioned
- [ ] Deployment guide written: `docs/deployment-guide.md`

---

### Story 10.5 — Playwright recording + git tag v1.0 `M`
**As a product owner**, I want a recorded demo of TanqitFlow v1.0 and a tagged release.

**Acceptance Criteria**:
- [ ] Playwright records all critical flows (reuses Sprint 9 E2E suite against production staging):
  - Login, CSV upload, water balance view, hotspot map, worklist, language switch FR → AR
- [ ] Recording saved: `.recordings/v1.0-2026-[date]-full.webm`
- [ ] `git tag v1.0` pushed to `github.com/rhorba/tanqitflow`
- [ ] GitHub Release created with: tag v1.0, release notes (features delivered), Docker image links
- [ ] `SESSION_END` logged to `.logs/sessions.md` with sprint retrospective summary

---

**Sprint 10 total**: ~26 SP | Est: 2 weeks

---

## Sprint Velocity Summary

| Sprint | Theme | Stories | Est. SP |
|--------|-------|---------|---------|
| 1 | Foundation & Infrastructure | 8 | 26 |
| 2 | Auth + Multi-Tenant Core | 7 | 25 |
| 3 | Data Ingestion Pipeline | 6 | 28 |
| 4 | Water Balance Engine | 5 | 24 |
| 5 | Leak Detection & Prioritization | 5 | 27 |
| 6 | Dashboard & Visualization | 4 | 25 |
| 7 | Bilingual UI (FR/AR + RTL) | 4 | 24 |
| 8 | Security Hardening | 5 | 28 |
| 9 | Testing & Quality Gate | 4 | 27 |
| 10 | Production Hardening & Ship | 5 | 26 |
| **TOTAL** | | **53 stories** | **~260 SP** |

---

## Definition of Done (applies to every story)

- [ ] Code pushed to feature branch; PR created and passes CI (lint + tests + coverage gate)
- [ ] PR reviewed (at least self-review with checklist)
- [ ] Tests written: unit test if business logic; integration test if API/DB; coverage gate maintained
- [ ] No hardcoded strings (env vars for config; i18n for UI copy)
- [ ] Both FR and AR translations added for any new UI string
- [ ] Audit log entry produced for any new write operation
- [ ] OpenAPI description updated for any new/changed endpoint
- [ ] `.logs/activity.md` entry added: COMPLETED: Story X.Y — [one-line summary]
- [ ] Merged to `main` after Sprint end; `git push origin main`

---
