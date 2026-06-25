# System Design — TanqitFlow v1.0

**Status**: APPROVED  
**Date**: 2026-06-25  
**Specialist**: System Designer

---

## 1. Non-Functional Requirements Capture

| Category | Target | Rationale |
|----------|--------|-----------|
| **Throughput** | 100K rows / 60 s per CSV import | Hundreds of DMAs × hundreds of customers per weekly/monthly batch |
| **Latency** | P95 < 500 ms read API, < 200 ms dashboard queries | Analyst interactive use; dashboard refresh |
| **Availability** | 99% on pilot VPS | Single-region Docker Compose; no HA requirement for pilot |
| **Scalability** | Vertical (scale-up VPS) for v1.0; horizontal considered in design | Pilot is single regional branch; multi-region is v2 |
| **Data volume** | ~300 DMAs × ~1,000 customer reads × 52 weeks = ~15M rows/year | TimescaleDB hypertables justified |
| **Retention** | 5 years (~75M rows total at full scale) | Law 09-08 + regulatory requirement |
| **Security** | STRIDE, DAST, RBAC, schema-per-tenant | Critical infrastructure + government data |
| **Deployment** | Docker Compose on VPS; Docker images pushed to GHCR | No managed cloud services required (data sovereignty) |

---

## 2. Component Topology

```
┌─────────────────────────────────────────────────────────────────────┐
│  CLIENT TIER                                                         │
│                                                                      │
│  Browser / Mobile (375px+)                                           │
│  React + Vite + TypeScript + Tailwind + i18next (FR/AR RTL)         │
│  Leaflet (map) · Recharts (charts) · TanStack Query (data fetching) │
└────────────────────────┬────────────────────────────────────────────┘
                         │ HTTPS (443)
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  INGRESS                                                             │
│  Nginx (reverse proxy, SSL termination, security headers)           │
└────────────────────────┬────────────────────────────────────────────┘
                         │ HTTP (8000, internal)
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  APPLICATION TIER                                                    │
│                                                                      │
│  FastAPI (Python 3.12)                                              │
│  ├── Auth router      (JWT issue/refresh/revoke)                    │
│  ├── Ingestion router (CSV upload, job status)                      │
│  ├── Balance router   (water balance compute + query)               │
│  ├── Detection router (leak scores, anomaly events)                 │
│  ├── Worklist router  (repair prioritization)                       │
│  ├── Dashboard router (aggregated KPIs + GeoJSON)                   │
│  ├── Admin router     (tenant + user management)                    │
│  └── Reports router   (PDF export)                                  │
│                                                                      │
│  Middleware stack:                                                   │
│  TenantContextMiddleware → AuthMiddleware → AuditLogMiddleware       │
└──────┬──────────────────────────────┬──────────────────────────────┘
       │ SQLAlchemy async             │ Celery task dispatch
       ▼                              ▼
┌─────────────────┐        ┌─────────────────────────────────────────┐
│  DATA TIER      │        │  ASYNC WORKER TIER                      │
│                 │        │                                         │
│  PostgreSQL 16  │        │  Celery Workers (Python 3.12)           │
│  + TimescaleDB  │        │  ├── csv_ingest_task                    │
│  + PostGIS      │        │  ├── water_balance_task                 │
│                 │        │  ├── leak_detection_task                │
│  Schema layout: │        │  ├── worklist_generate_task             │
│  public         │        │  └── pdf_report_task                    │
│  ├── tenants    │        │                                         │
│  ├── platform_  │        │  Celery Beat (scheduler)                │
│  │   audit_logs │        │  ├── nightly MNF computation            │
│  └── migrations │        │  └── monthly IF model retrain           │
│                 │        └─────────────────────┬───────────────────┘
│  tenant_abc     │                              │
│  ├── dma        │        ┌─────────────────────▼───────────────────┐
│  ├── dma_reading│        │  MESSAGE BROKER                         │
│  │  (hypertable)│        │  Redis 7 (Celery broker + result backend)│
│  ├── meter_reads│        │  + JWT refresh token blacklist          │
│  ├── water_     │        │  + rate-limit counters                  │
│  │   balance    │        └─────────────────────────────────────────┘
│  ├── leak_      │
│  │   indicators │        ┌─────────────────────────────────────────┐
│  ├── anomaly_   │        │  OBJECT STORAGE                         │
│  │   events     │        │  MinIO (S3-compatible)                  │
│  ├── worklist   │        │  Bucket: tanqitflow-uploads             │
│  ├── users      │        │  Path: /{tenant_slug}/{year}/{month}/   │
│  ├── audit_logs │        │  ├── raw/   (original uploaded files)   │
│  └── ...        │        │  └── reports/ (generated PDFs)         │
└─────────────────┘        └─────────────────────────────────────────┘
```

---

## 3. Data Flow Diagrams

### 3.1 CSV Ingestion Flow

```
Analyst uploads CSV
        │
        ▼
FastAPI: POST /ingestion/upload
        │
        ├─→ Validate file size (< 50MB)
        ├─→ Store raw file to MinIO (async, pre-signed URL)
        ├─→ Create IngestionJob record (status=QUEUED)
        ├─→ Dispatch Celery task: csv_ingest_task(job_id)
        └─→ Return { job_id, status: "QUEUED" }

Celery Worker: csv_ingest_task
        │
        ├─→ Fetch file from MinIO
        ├─→ Detect CSV type (DMA_INFLOW / CUSTOMER_READS / PRESSURE_FLOW)
        ├─→ Apply tenant column mapping
        ├─→ Validate rows (pandas dtype check + business rules)
        ├─→ Bulk insert to TimescaleDB hypertable
        │     (COPY via asyncpg for 100K rows/60s target)
        ├─→ Update IngestionJob: status=DONE, rows_processed, error_count
        └─→ Dispatch water_balance_task for affected DMAs + periods

Analyst polls: GET /ingestion/jobs/{id}
        └─→ Returns: { status, progress_pct, rows_processed, errors[] }
```

### 3.2 Water Balance + Leak Detection Flow

```
water_balance_task(dma_ids, period)
        │
        ├─→ Query dma_readings hypertable for period
        ├─→ Query meter_reads for period
        ├─→ Compute IWA components (pure Python domain service)
        ├─→ Store results in water_balance table
        ├─→ Dispatch leak_detection_task(dma_ids)
        └─→ Update job status

leak_detection_task(dma_ids)
        │
        ├─→ MNF analysis (02:00–04:00 window, 30-night baseline)
        ├─→ Z-score on 30-day rolling window
        ├─→ Load Isolation Forest model (if trained) → score
        ├─→ Combine signals → confidence_score (0–100)
        ├─→ Store in leak_indicators + anomaly_events
        └─→ Dispatch worklist_generate_task
```

### 3.3 Dashboard Query Flow

```
Browser: GET /dashboard/summary?tenant=abc&from=2026-01-01&to=2026-06-30
        │
        ▼
FastAPI TenantMiddleware
        ├─→ Decode JWT → extract tenant_slug + user_role
        ├─→ Set PostgreSQL search_path = tenant_slug
        └─→ RBAC check (field_viewer: only own DMAs)

Repository query
        ├─→ SELECT NRW% FROM water_balance WHERE period BETWEEN …
        │     (TimescaleDB time-series query, < 50ms with chunk index)
        ├─→ SELECT confidence_score FROM leak_indicators (recent)
        └─→ SELECT ST_AsGeoJSON(polygon) FROM dma (PostGIS)

Response: { kpis, trend_data[], dma_table[], geojson_layer }
        └─→ TanStack Query caches for 60s client-side
```

---

## 4. Integration Patterns

| Pattern | Used For | Technology |
|---------|----------|------------|
| Sync HTTP | All client ↔ API interactions | FastAPI + HTTPS via Nginx |
| Async task queue | CSV processing, balance compute, ML scoring, PDF gen | Celery + Redis |
| Scheduled tasks | Nightly MNF, monthly IF retrain | Celery Beat |
| Object storage | Raw CSV files, generated PDFs | MinIO S3 API (boto3) |
| Time-series storage | DMA readings, meter reads, anomaly events | TimescaleDB hypertables |
| Spatial data | DMA polygon boundaries | PostGIS geometry columns, ST_AsGeoJSON |
| Multi-tenant isolation | Per-tenant data separation | PostgreSQL schema-per-tenant |
| Cache | JWT blacklist, rate-limit counters, dashboard TTL cache | Redis |

---

## 5. Docker Compose Services

| Service | Image | Port (internal) | Depends On |
|---------|-------|-----------------|------------|
| `nginx` | nginx:alpine | 80, 443 (external) | frontend, api |
| `frontend` | tanqitflow-frontend (Vite build) | 3000 | — |
| `api` | tanqitflow-api (FastAPI + Gunicorn) | 8000 | db, redis, minio |
| `worker` | tanqitflow-api (Celery entrypoint) | — | db, redis, minio |
| `beat` | tanqitflow-api (Celery Beat entrypoint) | — | redis |
| `db` | timescale/timescaledb-ha:pg16-latest | 5432 | — |
| `redis` | redis:7-alpine | 6379 | — |
| `minio` | minio/minio:latest | 9000, 9001 | — |

**Total: 8 services**  
**Minimum VPS spec**: 4 vCPU / 8 GB RAM / 100 GB SSD

---

## 6. Scaling Strategy (Post-Pilot)

| Trigger | Action |
|---------|--------|
| CSV import > 60s for 100K rows | Add Celery worker replicas (horizontal) |
| Dashboard API > 500ms P95 | Add TimescaleDB continuous aggregates + materialized views |
| > 5 tenants | Move to Kubernetes (Docker Compose → K8s manifests) |
| > 10 tenants | Consider read replica for analytics queries |
| Multi-region ONEE | Add Redis Sentinel / Cluster; TimescaleDB streaming replication |

---
