# Product Requirements Document — TanqitFlow v1.0

**Status**: APPROVED  
**Date**: 2026-06-25  
**Owner**: Mohamed Rhorba  
**Pilot target**: ONEE — single regional branch (Rabat or Casablanca)

---

## 1. Problem Statement

Moroccan water utilities (ONEE and the 18 regional SRM distributors) lose large volumes of treated water to leaks, metering errors, and theft — collectively called **Non-Revenue Water (NRW)**. ONEE's 2025–2030 investment plan is funded specifically to cut distribution losses.

**Why it's urgent:**
- Per-capita water availability is falling toward 480 m³/year by 2030
- Desalinated water costs ~4× conventional supply (~16 MAD/m³ vs ~4 MAD/m³)
- Most utilities still track NRW manually in Excel — no systematic leak prioritization, no repair ROI calculation
- Reducing NRW is the cheapest available new water source

**TanqitFlow** replaces manual tracking with an automated, data-driven NRW intelligence platform that ingests ERP exports, computes the IWA water balance, detects and localizes leaks, and ranks repairs by cubic-meters-saved per dirham.

---

## 2. Goals & Success Metrics

| Goal | Success Metric |
|------|---------------|
| Automate IWA water balance | NRW % computed < 5 min after CSV upload |
| Detect and localize leaks | Top-10 DMAs flagged with confidence score ≥ 70% |
| Prioritize repairs by ROI | Repair worklist ranked by m³ saved per MAD, exportable |
| Provide management visibility | Dashboard loads < 3s for 300 DMAs |
| Secure multi-tenant isolation | 0 cross-tenant data leaks (schema-per-tenant + adversarial test) |
| Bilingual government-ready UI | Full FR + AR (RTL) with 0 hardcoded strings |

---

## 3. Users & Personas

### P1 — Utility Admin (ONEE Regional Director)
- Creates and manages user accounts within their tenant
- Views high-level NRW % summary across all DMAs in their region
- Exports management reports in French or Arabic
- Configures water cost per m³ for ROI calculations

### P2 — NRW Analyst (ONEE/SRM Technical Engineer)
- Uploads CSV exports from billing ERP (SAP, Oracle, or local custom)
- Reviews water balance results per DMA and per period
- Investigates leak candidates on the hotspot map
- Manages and updates the repair worklist

### P3 — Field Viewer (Field Supervisor / Network Inspector)
- Views assigned DMAs on a map (mobile-responsive)
- Sees repair priorities and task status
- Cannot upload data or modify configuration
- Reads reports in Arabic (primary language in the field)

---

## 4. Scope

### In-scope — MVP v1.0

1. **Data ingestion**: CSV upload (DMA inflow meters, customer meter reads, SCADA pressure/flow) — batch, weekly or monthly frequency from ERP
2. **Water balance engine**: IWA method (SIV, BAC, UAC, AL metering, AL theft, RL, NRW, NRW%)
3. **Leak detection**: Minimum Night Flow (MNF) analysis + z-score + Isolation Forest per DMA
4. **Prioritization**: DMA ranking by estimated loss volume × water cost per dirham; repair worklist
5. **Dashboard**: Per-region + per-DMA NRW%, trend lines, hotspot map, repair worklist
6. **Bilingual UI**: French + Arabic (RTL) — from Sprint 1
7. **Multi-tenant RBAC**: Schema-per-tenant isolation; 3 roles (utility_admin / analyst / field_viewer)
8. **Security**: STRIDE, adversarial review, RBAC, audit logging, Law 09-08 compliance, OWASP ZAP DAST
9. **Deployment**: Docker Compose + GitHub Actions CI/CD → VPS

### Out of scope — YAGNI (post-v1.0 backlog)

- Live SCADA streaming (real-time WebSocket ingestion)
- IoT sensor direct TCP/MQTT integration
- Automated field crew dispatch / work order system
- Financial billing / invoicing
- SMS / email alert notifications (post-pilot)
- Native mobile app (responsive web is sufficient for field viewer)
- LDAP / Active Directory SSO
- BI connector exports (Power BI, Tableau, Metabase)
- Pressure district optimizer (demand modeling)

---

## 5. Functional Requirements

### FR-01: Data Ingestion

| ID | Requirement |
|----|-------------|
| REQ-01.1 | System accepts CSV/Excel file uploads up to 50 MB per file |
| REQ-01.2 | System validates format (columns, types, encoding, UTF-8 or Windows-1256) before processing |
| REQ-01.3 | CSV processing is asynchronous (Celery task); UI shows progress % |
| REQ-01.4 | Raw uploaded files are stored in MinIO with immutable audit trail (filename, uploader, timestamp, SHA-256 hash) |
| REQ-01.5 | System supports three CSV types: `DMA_INFLOW`, `CUSTOMER_READS`, `PRESSURE_FLOW` |
| REQ-01.6 | Column mapping is configurable per tenant (ERP exports vary) |
| REQ-01.7 | Import errors returned as row-level list: row_number, column, error_message |

### FR-02: Water Balance Engine (IWA Method)

| ID | Requirement |
|----|-------------|
| REQ-02.1 | Compute per DMA per billing period: SIV, BAC, UAC, AL_metering, AL_theft, RL, NRW, NRW% |
| REQ-02.2 | Support configurable period: monthly or quarterly |
| REQ-02.3 | Water cost per m³ is configurable per tenant (conventional vs desalinated) |
| REQ-02.4 | Aggregate per-DMA results to per-region totals |
| REQ-02.5 | Store historical water balance records; expose last 12 periods for trend analysis |
| REQ-02.6 | Loss value in MAD = NRW_m3 × water_cost_per_m3 |

### FR-03: Leak Detection

| ID | Requirement |
|----|-------------|
| REQ-03.1 | Compute Minimum Night Flow (MNF) per DMA from flow time-series (02:00–04:00 window) |
| REQ-03.2 | Flag DMAs where MNF > baseline_MNF × configurable_threshold (default 1.5×) |
| REQ-03.3 | Apply z-score anomaly detection on flow and pressure (30-day rolling window; flag |z| > 3) |
| REQ-03.4 | Apply Isolation Forest on flow + pressure features per DMA (weekly scoring; monthly retrain) |
| REQ-03.5 | Output leak confidence score (0–100) per DMA, combining MNF + z-score + Isolation Forest signals |

### FR-04: Prioritization & Worklist

| ID | Requirement |
|----|-------------|
| REQ-04.1 | Rank DMAs: score = estimated_loss_m3/month × water_cost/m3 × leak_confidence |
| REQ-04.2 | Worklist fields: rank, dma_id, dma_name, loss_m3_est, savings_mad_est/month, confidence%, alert_type |
| REQ-04.3 | Analyst can set worklist item status: OPEN / IN_PROGRESS / RESOLVED / DEFERRED |
| REQ-04.4 | Worklist exportable as CSV and bilingual PDF |

### FR-05: Dashboard

| ID | Requirement |
|----|-------------|
| REQ-05.1 | KPI cards: total SIV m³, total NRW m³, NRW%, count of flagged DMAs |
| REQ-05.2 | NRW% trend chart (Recharts) for last 1/3/6/12 months |
| REQ-05.3 | Sortable DMA table: name, SIV, BAC, NRW m³, NRW%, trend indicator, leak flag |
| REQ-05.4 | DMA detail page: full IWA breakdown, time-series chart, anomaly events |
| REQ-05.5 | Hotspot map: PostGIS GeoJSON polygons color-coded by NRW% severity |
| REQ-05.6 | Map layer toggle: NRW%, leak confidence, pressure anomalies |
| REQ-05.7 | Dashboard loads < 3 seconds for 300 DMAs |

### FR-06: Bilingual UI

| ID | Requirement |
|----|-------------|
| REQ-06.1 | All UI text in French and Arabic (0 hardcoded strings) |
| REQ-06.2 | Arabic mode: RTL layout, dir="rtl", mirrored navigation |
| REQ-06.3 | Language preference persists in localStorage |
| REQ-06.4 | PDF reports generated in user's active language |

### FR-07: Multi-Tenant & RBAC

| ID | Requirement |
|----|-------------|
| REQ-07.1 | Each ONEE region + each SRM distributor is a separate, isolated tenant |
| REQ-07.2 | Tenant isolation implemented as schema-per-tenant in PostgreSQL |
| REQ-07.3 | Roles: `utility_admin` (full access), `analyst` (read/write data, no user mgmt), `field_viewer` (read assigned DMAs only) |
| REQ-07.4 | utility_admin can provision and manage users within their tenant only |
| REQ-07.5 | Cross-tenant data access impossible at DB level (search_path enforcement) |

### FR-08: Security & Compliance

| ID | Requirement |
|----|-------------|
| REQ-08.1 | All API endpoints require JWT (except /health, /auth/login, /auth/refresh) |
| REQ-08.2 | All write operations produce an audit log entry (user, action, resource, IP, timestamp, before/after JSON) |
| REQ-08.3 | PII fields (customer_name, customer_ref, national_id) tagged and encrypted (AES-256, pgcrypto) |
| REQ-08.4 | STRIDE threat model documented and all Medium+ findings mitigated |
| REQ-08.5 | OWASP ZAP DAST scan: 0 High/Critical findings before ship |
| REQ-08.6 | Adversarial review checklist passed on auth + tenant isolation |
| REQ-08.7 | Law 09-08 data processing register maintained |
| REQ-08.8 | Brute force protection: 5 failed login attempts → 15-min lockout (Redis) |

---

## 6. Non-Functional Requirements

| NFR | Target |
|-----|--------|
| API P95 response time | < 500 ms for read queries on 300 DMAs |
| CSV processing throughput | 100K rows < 60 seconds (Celery worker) |
| Availability (pilot VPS) | 99% uptime (Docker healthchecks + restart policies) |
| Data retention | 5 years (Law 09-08 + regulatory) |
| Deployment unit | Docker Compose; min VPS 4 vCPU / 8 GB RAM |
| Test coverage | ≥ 80% combined unit + integration (CI gate) |
| Browser support | Chrome 120+, Firefox 120+, Safari 17+ |
| Mobile / responsive | Down to 375 px width (field viewer use case) |
| Language | Python 3.12, Node 20 LTS |

---

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| ERP CSV format varies across utilities | High | High | Configurable column-mapping per tenant |
| Missing DMA boundary polygons (PostGIS) | Medium | Medium | Support manual GeoJSON upload; fallback to list view if no geodata |
| Isolation Forest needs labelled data for tuning | High | Medium | Default to z-score; IF as opt-in feature; retrain monthly |
| Government procurement timeline slips | High | Low | Self-serve demo mode with synthetic data |
| TimescaleDB migration complexity | Low | Medium | Wrap in abstracted repository layer; feature flag to disable |
| Law 09-08 CNDP registration requirement | Medium | High | Include legal checklist; data processing register doc auto-generated |

---

## 8. Out of Scope Decisions Log

| Item | Reason |
|------|--------|
| Live SCADA streaming | Adds MQTT/WebSocket complexity without pilot need (batch CSV confirmed) |
| SMS/email alerts | Post-pilot; requires carrier API setup per country |
| LDAP/AD SSO | Q3: Docker + GitHub CI/CD = standard JWT is sufficient |
| Native mobile | Responsive web covers field_viewer persona |
| TimescaleDB compression policies | Add after pilot confirms retention volume |
| ML model serving API | sklearn in-process is sufficient for weekly batch scoring |

---
