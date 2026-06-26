# TanqitFlow — STRIDE Threat Model

**Version**: 1.0 | **Date**: 2026-06-26 | **Author**: Security Engineer  
**Components in scope**: Auth, Tenant Isolation, Data Ingestion, Water Balance API, Worklist, PDF Generation

---

## STRIDE Legend

| Category | Meaning |
|----------|---------|
| S | Spoofing — impersonating a user or service |
| T | Tampering — modifying data or code |
| R | Repudiation — denying an action occurred |
| I | Information Disclosure — exposing data to unauthorized parties |
| D | Denial of Service — making the system unavailable |
| E | Elevation of Privilege — gaining unauthorized permissions |

**Risk rating**: Likelihood (H/M/L) × Impact (H/M/L) → Risk (Critical/High/Medium/Low)

---

## 1. Auth (JWT + Redis Blacklist)

| ID | Category | Threat | Likelihood | Impact | Risk | Mitigation | Status |
|----|----------|--------|-----------|--------|------|------------|--------|
| A-01 | S | Attacker forges JWT by guessing secret | L | H | Medium | HS256 + 256-bit random secret; rotation procedure documented below | MITIGATED |
| A-02 | T | Attacker tampers JWT payload (e.g., role elevation) | L | H | Medium | HMAC signature verified on every request in `core/security.py` | MITIGATED |
| A-03 | R | User denies performing a write action | M | M | Medium | AuditLogMiddleware appends to tenant `audit_log` (append-only, no UPDATE/DELETE) | MITIGATED |
| A-04 | I | JWT leaked in logs or network | M | H | High | Short-lived access tokens (15 min); HTTPS-only in production | MITIGATED |
| A-05 | D | Brute-force login attempt | H | M | High | Redis rate-limit: 5 attempts → 429 lockout for 15 min | MITIGATED |
| A-06 | E | Refresh token replay after logout | M | H | High | Redis blacklist stores revoked refresh tokens; `POST /auth/logout` adds to blacklist | MITIGATED |

**JWT Secret Rotation Procedure**:
1. Generate new secret: `openssl rand -hex 32`
2. Update `JWT_SECRET` in `.env` and re-deploy API + worker containers
3. All existing tokens immediately become invalid → users re-login
4. Rotate quarterly or on suspected compromise

---

## 2. Tenant Isolation (Schema-per-Tenant)

| ID | Category | Threat | Likelihood | Impact | Risk | Mitigation | Status |
|----|----------|--------|-----------|--------|------|------------|--------|
| T-01 | I | Tenant A reads Tenant B's data via API | L | H | High | `TenantContextMiddleware` sets `search_path` to tenant's schema per request | MITIGATED |
| T-02 | E | Analyst from Tenant A gets JWT; calls Tenant B endpoint | L | H | High | JWT encodes `tenant_slug`; `require_role` checks `tenant_id` matches token | MITIGATED |
| T-03 | T | Raw SQL injection via DMA code parameter | L | H | High | All queries use SQLAlchemy parameterized statements (`:param` syntax); no string interpolation in WHERE clauses | MITIGATED |
| T-04 | S | Attacker uses another tenant's valid JWT against different subdomain | L | H | High | `tenant_slug` in JWT validated against DB on every request | MITIGATED |

---

## 3. Data Ingestion API (CSV Upload)

| ID | Category | Threat | Likelihood | Impact | Risk | Mitigation | Status |
|----|----------|--------|-----------|--------|------|------------|--------|
| I-01 | T | CSV formula injection (`=cmd|'/c calc'`) | H | M | High | `sanitize_csv_cell()` in `core/pii.py` prepends `'` to cells starting with `= + - @ | ^` | MITIGATED |
| I-02 | T | Upload `.php` disguised as `.csv` (MIME mismatch) | M | H | High | `validate_file_magic()` checks first bytes, not client-supplied Content-Type | MITIGATED |
| I-03 | D | 1 GB upload floods memory/disk | L | H | High | 50 MB hard limit enforced before `file.read()` in upload handler | MITIGATED |
| I-04 | I | Raw file accessible in MinIO without auth | L | H | High | MinIO bucket is private; presigned URLs used for download with expiry | MITIGATED |
| I-05 | R | Uploader denies submitting a file | M | M | Medium | `ingestion_jobs` table records user_id, original filename, timestamp | MITIGATED |

---

## 4. Water Balance API

| ID | Category | Threat | Likelihood | Impact | Risk | Mitigation | Status |
|----|----------|--------|-----------|--------|------|------------|--------|
| B-01 | T | Analyst manipulates balance parameters (e.g., negative SIV) | M | M | Medium | Pydantic schema validation with `ge=0` constraints on all numeric inputs | MITIGATED |
| B-02 | I | Unauthorized read of balance data | L | M | Low | `get_current_user` dependency required on all balance endpoints | MITIGATED |
| B-03 | D | Large date range query times out | M | M | Medium | `months` param capped at 60; TimescaleDB hypertable indexes period_start | MITIGATED |

---

## 5. Worklist

| ID | Category | Threat | Likelihood | Impact | Risk | Mitigation | Status |
|----|----------|--------|-----------|--------|------|------------|--------|
| W-01 | E | `field_viewer` generates or exports worklist | M | M | Medium | `POST /worklist/generate` and `GET /worklist/export` require analyst+ role | MITIGATED |
| W-02 | T | Status transition to invalid state (e.g., DEFERRED → OPEN) | L | L | Low | Pydantic `WorklistStatus` enum — only valid values accepted | MITIGATED |
| W-03 | I | CSV export includes sensitive tenant data | M | M | Medium | Export only serves the requesting tenant's data (tenant isolation enforced) | MITIGATED |

---

## 6. PDF Generation (WeasyPrint)

| ID | Category | Threat | Likelihood | Impact | Risk | Mitigation | Status |
|----|----------|--------|-----------|--------|------|------------|--------|
| P-01 | T | Path traversal via `from_date` / `to_date` parameter | L | H | High | Pydantic `pattern=r"^\d{4}-\d{2}-\d{2}$"` validates date format strictly | MITIGATED |
| P-02 | E | Server-Side Template Injection via report data | L | H | High | Jinja2 uses `autoescape=True` context; report data rendered as string values only | MITIGATED |
| P-03 | D | PDF generation task hangs, blocking worker queue | M | M | Medium | Celery task has `max_retries=2`; WeasyPrint runs in isolated worker process | MITIGATED |
| P-04 | I | PDF report stored in MinIO accessible to other tenants | L | H | High | MinIO key prefixed with `{tenant_slug}/reports/` — presigned URL scoped to key | MITIGATED |

---

## Accepted Risks

None. All Medium+ risks are MITIGATED.

---

## Review Schedule

Threat model reviewed quarterly or on any new external-facing endpoint.
