# Software Architecture — TanqitFlow v1.0

**Status**: APPROVED  
**Date**: 2026-06-25  
**Specialist**: Software Architect + Tech Lead + DBA + Security Engineer

---

## 1. Architecture Style

**Layered Monolith with Domain Services**

Chosen over Hexagonal/Clean for a v1.0 monolith because:
- Faster to scaffold; team can move to hexagonal when the codebase justifies it
- FastAPI's dependency injection provides sufficient decoupling without full ports/adapters overhead
- Domain services (IWA engine, leak detector) are pure Python modules — easily extracted to microservices in v2

```
┌──────────────────────────────────────┐
│  API Layer (routers, request models)  │  ← HTTP boundary
├──────────────────────────────────────┤
│  Service Layer (business logic)       │  ← orchestrates domain
├──────────────────────────────────────┤
│  Domain Layer (pure business rules)   │  ← no I/O; fully testable
├──────────────────────────────────────┤
│  Repository Layer (DB access)         │  ← SQLAlchemy + asyncpg
├──────────────────────────────────────┤
│  Infrastructure (DB, Redis, MinIO)    │  ← I/O only here
└──────────────────────────────────────┘
```

---

## 2. Module / Package Structure

### Backend (`api/`)

```
api/
├── main.py                      ← FastAPI app factory, middleware registration
├── config.py                    ← Pydantic Settings (reads .env)
├── database.py                  ← Async engine, session factory, tenant schema ctx
│
├── routers/                     ← HTTP handlers only (thin)
│   ├── auth.py
│   ├── ingestion.py
│   ├── balance.py
│   ├── detection.py
│   ├── worklist.py
│   ├── dashboard.py
│   ├── admin.py
│   └── reports.py
│
├── services/                    ← Business logic (orchestrates domain + repos)
│   ├── auth_service.py
│   ├── ingestion_service.py
│   ├── balance_service.py
│   ├── detection_service.py
│   ├── worklist_service.py
│   └── report_service.py
│
├── domain/                      ← Pure business rules (no I/O, no DB)
│   ├── iwa_engine.py            ← IWA water balance algorithm
│   ├── mnf_calculator.py        ← Minimum Night Flow analysis
│   ├── zscore_detector.py       ← Z-score anomaly detection
│   ├── isolation_forest.py      ← Isolation Forest ML model wrapper
│   ├── worklist_ranker.py       ← Repair ROI scoring
│   └── models/                  ← Pure data classes (Pydantic, no ORM)
│       ├── water_balance.py
│       ├── leak_indicator.py
│       └── worklist_item.py
│
├── repositories/                ← DB access (SQLAlchemy async)
│   ├── base.py                  ← Generic CRUD; sets search_path for tenant
│   ├── dma_repo.py
│   ├── reading_repo.py
│   ├── balance_repo.py
│   ├── detection_repo.py
│   ├── worklist_repo.py
│   ├── user_repo.py
│   └── audit_repo.py
│
├── models/                      ← SQLAlchemy ORM models
│   ├── base.py
│   ├── dma.py
│   ├── dma_reading.py           ← TimescaleDB hypertable
│   ├── meter_read.py
│   ├── water_balance.py
│   ├── leak_indicator.py
│   ├── anomaly_event.py
│   ├── worklist_item.py
│   ├── ingestion_job.py
│   ├── user.py
│   └── audit_log.py
│
├── middleware/
│   ├── tenant.py                ← TenantContextMiddleware: decode JWT → set schema
│   ├── audit.py                 ← AuditLogMiddleware: log all writes
│   └── ratelimit.py             ← Redis-backed rate limiter
│
├── tasks/                       ← Celery tasks
│   ├── celery_app.py
│   ├── ingest_task.py
│   ├── balance_task.py
│   ├── detection_task.py
│   ├── worklist_task.py
│   ├── report_task.py
│   └── retrain_task.py          ← Monthly IF model retrain (Beat)
│
├── schemas/                     ← Pydantic request/response schemas
│   ├── auth.py
│   ├── ingestion.py
│   ├── balance.py
│   ├── detection.py
│   ├── worklist.py
│   └── dashboard.py
│
├── core/
│   ├── security.py              ← JWT creation/verification, password hashing
│   ├── permissions.py           ← RBAC decorators / dependency
│   ├── exceptions.py            ← Custom HTTP exceptions
│   └── pagination.py
│
└── tests/
    ├── unit/
    │   ├── test_iwa_engine.py
    │   ├── test_mnf_calculator.py
    │   ├── test_zscore_detector.py
    │   ├── test_isolation_forest.py
    │   ├── test_worklist_ranker.py
    │   └── test_csv_parsers.py
    ├── integration/
    │   ├── test_ingestion_api.py
    │   ├── test_balance_api.py
    │   ├── test_detection_api.py
    │   ├── test_auth_api.py
    │   └── test_tenant_isolation.py
    └── conftest.py              ← pytest fixtures (test DB, test client, tenant setup)
```

### Frontend (`frontend/`)

```
frontend/
├── index.html
├── vite.config.ts
├── tailwind.config.ts           ← RTL plugin enabled
│
├── src/
│   ├── main.tsx
│   ├── App.tsx                  ← Router + i18next provider + RTL dir toggle
│   │
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Dashboard.tsx        ← KPI cards + trend chart
│   │   ├── DmaTable.tsx         ← Sortable DMA list
│   │   ├── DmaDetail.tsx        ← Full IWA breakdown + charts
│   │   ├── Map.tsx              ← Leaflet hotspot map
│   │   ├── Worklist.tsx         ← Repair prioritization list
│   │   ├── Ingestion.tsx        ← CSV upload + job history
│   │   ├── Admin.tsx            ← User + tenant management
│   │   └── Reports.tsx          ← PDF export
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx       ← Language switcher
│   │   │   └── Layout.tsx
│   │   ├── charts/
│   │   │   ├── NrwTrendChart.tsx
│   │   │   └── BalanceBreakdown.tsx
│   │   ├── map/
│   │   │   └── HotspotMap.tsx
│   │   └── ui/                  ← Shared: Button, Badge, Table, Card, etc.
│   │
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useTenant.ts
│   │   └── useDashboard.ts
│   │
│   ├── api/                     ← TanStack Query hooks + axios client
│   │   ├── client.ts            ← axios instance with JWT interceptor
│   │   ├── auth.ts
│   │   ├── ingestion.ts
│   │   ├── balance.ts
│   │   ├── detection.ts
│   │   └── worklist.ts
│   │
│   ├── store/
│   │   └── authStore.ts         ← Zustand: user, token, tenant
│   │
│   ├── i18n/
│   │   ├── index.ts             ← i18next config
│   │   ├── fr/
│   │   │   ├── common.json
│   │   │   ├── dashboard.json
│   │   │   └── ...
│   │   └── ar/
│   │       ├── common.json
│   │       ├── dashboard.json
│   │       └── ...
│   │
│   └── types/
│       └── api.ts               ← TypeScript interfaces matching API schemas
│
└── tests/
    └── e2e/                     ← Playwright tests
        ├── auth.spec.ts
        ├── ingestion.spec.ts
        ├── dashboard.spec.ts
        ├── map.spec.ts
        ├── worklist.spec.ts
        └── i18n.spec.ts
```

---

## 3. Database Schema (per-tenant)

### Schema Strategy: Schema-per-Tenant

```sql
-- public schema: platform metadata only
CREATE SCHEMA public;
CREATE TABLE public.tenants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug        VARCHAR(50) UNIQUE NOT NULL,  -- used as schema name
    name        VARCHAR(200) NOT NULL,
    region      VARCHAR(100),
    cost_conventional_mad  NUMERIC(8,4) DEFAULT 4.0,
    cost_desalinated_mad   NUMERIC(8,4) DEFAULT 16.0,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    is_active   BOOLEAN DEFAULT TRUE
);

-- Each tenant gets its own schema: CREATE SCHEMA {tenant_slug}
-- search_path set per-request in TenantContextMiddleware

-- Per-tenant schema tables:

-- DMA (District Metered Area)
CREATE TABLE dma (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code        VARCHAR(50) UNIQUE NOT NULL,
    name        VARCHAR(200) NOT NULL,
    name_ar     VARCHAR(200),
    polygon     GEOMETRY(MULTIPOLYGON, 4326),  -- PostGIS
    area_km2    NUMERIC(10,4),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- DMA readings (TimescaleDB hypertable, partitioned by week)
CREATE TABLE dma_reading (
    time        TIMESTAMPTZ NOT NULL,
    dma_id      UUID NOT NULL REFERENCES dma(id),
    flow_m3     NUMERIC(12,3),
    pressure_bar NUMERIC(8,3)
);
SELECT create_hypertable('dma_reading', 'time', chunk_time_interval => INTERVAL '1 week');
CREATE INDEX ON dma_reading (dma_id, time DESC);

-- Customer meter reads
CREATE TABLE meter_read (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dma_id          UUID NOT NULL REFERENCES dma(id),
    meter_id        VARCHAR(50) NOT NULL,
    customer_ref    BYTEA,   -- AES-256 encrypted (PII, Law 09-08)
    read_date       DATE NOT NULL,
    read_m3         NUMERIC(12,3) NOT NULL,
    consumption_m3  NUMERIC(12,3),
    is_estimated    BOOLEAN DEFAULT FALSE,
    UNIQUE(meter_id, read_date)
);

-- IWA water balance (computed, per DMA per period)
CREATE TABLE water_balance (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dma_id      UUID NOT NULL REFERENCES dma(id),
    period_start DATE NOT NULL,
    period_end   DATE NOT NULL,
    siv_m3      NUMERIC(14,3),   -- System Input Volume
    bac_m3      NUMERIC(14,3),   -- Billed Authorized Consumption
    uac_m3      NUMERIC(14,3),   -- Unbilled Authorized Consumption
    al_metering_m3 NUMERIC(14,3), -- Apparent Loss: metering errors
    al_theft_m3    NUMERIC(14,3), -- Apparent Loss: theft
    rl_m3          NUMERIC(14,3), -- Real Losses
    nrw_m3         NUMERIC(14,3), -- Non-Revenue Water = SIV - BAC
    nrw_pct        NUMERIC(6,2),  -- NRW %
    nrw_value_mad  NUMERIC(14,2), -- NRW in MAD
    computed_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(dma_id, period_start, period_end)
);

-- Leak indicators (per DMA, rolling)
CREATE TABLE leak_indicator (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dma_id              UUID NOT NULL REFERENCES dma(id),
    computed_at         TIMESTAMPTZ DEFAULT NOW(),
    mnf_m3h             NUMERIC(10,3),
    mnf_baseline_m3h    NUMERIC(10,3),
    mnf_flag            BOOLEAN DEFAULT FALSE,
    zscore_max          NUMERIC(8,3),
    zscore_flag         BOOLEAN DEFAULT FALSE,
    if_anomaly_score    NUMERIC(6,4),  -- 0-1
    confidence_score    SMALLINT,      -- 0-100 combined
    alert_type          VARCHAR(50)    -- 'MNF' | 'ZSCORE' | 'ISOLATION_FOREST' | 'COMBINED'
);

-- Anomaly events (detailed time-series anomaly records)
CREATE TABLE anomaly_event (
    time        TIMESTAMPTZ NOT NULL,
    dma_id      UUID NOT NULL REFERENCES dma(id),
    metric      VARCHAR(20) NOT NULL,  -- 'flow' | 'pressure'
    value       NUMERIC(12,3),
    zscore      NUMERIC(8,3),
    is_anomaly  BOOLEAN DEFAULT TRUE
);
SELECT create_hypertable('anomaly_event', 'time', chunk_time_interval => INTERVAL '1 month');

-- Repair worklist
CREATE TABLE worklist_item (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dma_id          UUID NOT NULL REFERENCES dma(id),
    rank            INTEGER NOT NULL,
    loss_m3_est     NUMERIC(14,3),
    savings_mad_est NUMERIC(14,2),
    confidence      SMALLINT,
    alert_type      VARCHAR(50),
    status          VARCHAR(20) DEFAULT 'OPEN',  -- OPEN | IN_PROGRESS | RESOLVED | DEFERRED
    updated_by      UUID REFERENCES users(id),
    updated_at      TIMESTAMPTZ,
    generated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Users (per tenant)
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       BYTEA NOT NULL,  -- encrypted PII
    role            VARCHAR(30) NOT NULL,  -- utility_admin | analyst | field_viewer
    assigned_dmas   UUID[],  -- for field_viewer: restricted DMA list
    is_active       BOOLEAN DEFAULT TRUE,
    failed_logins   SMALLINT DEFAULT 0,
    locked_until    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Ingestion jobs
CREATE TABLE ingestion_job (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename        VARCHAR(500),
    file_type       VARCHAR(30),   -- DMA_INFLOW | CUSTOMER_READS | PRESSURE_FLOW
    minio_key       VARCHAR(500),
    sha256          VARCHAR(64),
    status          VARCHAR(20) DEFAULT 'QUEUED',  -- QUEUED|PROCESSING|DONE|ERROR
    progress_pct    SMALLINT DEFAULT 0,
    rows_processed  INTEGER DEFAULT 0,
    error_count     INTEGER DEFAULT 0,
    errors_json     JSONB,
    uploaded_by     UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

-- Audit log (append-only)
CREATE TABLE audit_log (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID REFERENCES users(id),
    action          VARCHAR(100) NOT NULL,
    resource_type   VARCHAR(100) NOT NULL,
    resource_id     UUID,
    ip_address      INET,
    user_agent      TEXT,
    before_json     JSONB,
    after_json      JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
-- No UPDATE or DELETE on audit_log — enforced at application level + DB trigger
```

---

## 4. Design Patterns

| Pattern | Applied To | Reason |
|---------|-----------|--------|
| Repository pattern | All DB access | Isolates persistence; enables test mocking |
| Strategy pattern | CSV parser per file type | Each ERP format is a strategy; swappable |
| Domain service | IWA engine, MNF, z-score, IF | Pure Python, no I/O; fully unit-testable |
| Dependency injection | FastAPI `Depends()` | Auth, tenant context, DB session per request |
| Task queue (Command) | Celery tasks | Decouple upload from processing; async progress |
| Observer (audit) | AuditLogMiddleware | Cross-cutting; doesn't pollute business logic |

---

## 5. Dependency Rules

```
routers → services → domain (no reverse dependencies)
services → repositories (never domain → repositories directly)
tasks → services (Celery tasks are entry points, not business logic)
middleware → core/security, core/permissions (cross-cutting only)
```

**Forbidden**:
- Routers importing from repositories directly
- Domain modules importing from models (ORM) — domain uses pure Pydantic models
- Tests importing from infrastructure (use fixtures + test DB)

---

## 6. Key ADRs (Architecture Decision Records)

### ADR-001: Schema-per-Tenant over Row-Level Security
**Decision**: Use PostgreSQL schema-per-tenant  
**Rationale**: TanqitFlow is classified critical infrastructure (risk tier 13–15). Schema isolation provides a DB-level hard boundary even if application bugs occur. RLS is sufficient for SaaS apps but not for government utility data at this risk tier.  
**Consequences**: Tenant provisioning must create DB schema; migrations must run per tenant; Alembic configured for multi-schema operation.

### ADR-002: TimescaleDB for Time-Series Data
**Decision**: Use TimescaleDB hypertables for `dma_reading` and `anomaly_event`  
**Rationale**: 300 DMAs × 1,000 customers × 52 weeks = ~15M rows/year. TimescaleDB chunk pruning and native time-range indexes provide 10–100× faster queries vs plain Postgres on this workload.  
**Consequences**: Timescale Docker image instead of vanilla Postgres; hypertable DDL in migrations; requires `create_hypertable()` after CREATE TABLE.

### ADR-003: Celery + Redis over FastAPI BackgroundTasks
**Decision**: Use Celery with Redis broker for all async processing  
**Rationale**: FastAPI BackgroundTasks run in the same process — a large CSV (50 MB, 100K rows) would block the event loop and make the API unresponsive. Celery workers run as separate processes, support progress reporting, and can be scaled horizontally.  
**Consequences**: Redis required; worker Docker service; slightly more setup complexity.

### ADR-004: Isolation Forest as opt-in / graduated feature
**Decision**: Ship z-score as default anomaly detector; Isolation Forest as opt-in, disabled by tenant flag until 90 days of data accumulated  
**Rationale**: IF requires a training corpus; a new tenant has no historical data. Shipping it as default would produce random scores for the first 3 months.  
**Consequences**: Tenant config flag `enable_ml_detection: bool`; IF model stored per-tenant in MinIO; retrain job checks if enough data before running.

### ADR-005: Nginx in docker-compose.prod.yml only
**Decision**: Nginx added only to production Compose; development uses uvicorn directly  
**Rationale**: YAGNI for dev loop speed; Nginx adds no value locally and complicates hot-reload. Separate prod Compose file ensures dev stays simple.

---

## 7. Security Architecture (STRIDE Summary)

| Threat | Component | Mitigation |
|--------|-----------|-----------|
| **S**poofing — JWT forgery | Auth | HS256 + per-tenant secret; refresh token rotation; blacklist in Redis |
| **T**ampering — CSV manipulation | Ingestion | SHA-256 stored at upload; MinIO object lock; audit trail |
| **R**epudiation — deny write actions | All writes | Append-only audit_log; before/after JSON; IP + user agent |
| **I**nformation disclosure — cross-tenant | Data layer | Schema-per-tenant; search_path enforced in middleware; adversarial tests |
| **D**enial of service — large CSV | Ingestion | 50 MB file limit; async worker; Nginx client_max_body_size |
| **E**levation of privilege — role bypass | RBAC | Role checked in FastAPI dependency; 403 on violation; no role above own |

---

## 8. Law 09-08 Compliance Checklist

| Requirement | Implementation |
|-------------|---------------|
| Lawful basis documented | Data processing register (`docs/data-processing-register.md`) |
| PII minimization | Only meter_id + customer_ref stored; no names unless needed |
| PII encryption | `customer_ref`, `full_name` encrypted AES-256 (pgcrypto) |
| Right to erasure | Tenant delete archives PII; meter_read customer_ref → null on erasure |
| Data retention limit | 5 years; Celery Beat archival job after 5 years |
| CNDP registration | Template included in `docs/cndp-registration-template.md` |

---
