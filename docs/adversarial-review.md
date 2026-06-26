# TanqitFlow — Adversarial Review Checklist

**Version**: 1.0 | **Date**: 2026-06-26 | **Reviewer**: Security Engineer  
**Scope**: Auth boundaries, tenant isolation, RBAC, injection vectors

---

## Methodology

Each item specifies the test method, expected result, and verification code path.  
**PASS** = behavior matches expected. **FAIL** = defect — fix required before Sprint 9.

---

## Auth Boundary Tests

| # | Test | Method | Expected | Code Path | Result |
|---|------|--------|----------|-----------|--------|
| 1 | Expired JWT | Send request with token where `exp` is in the past | 401 Unauthorized | `core/security.py:verify_token` — `JWTError` raises 401 | **PASS** |
| 2 | Tampered JWT payload (role: "utility_admin") | Modify payload bytes, keep original signature | 401 Unauthorized | HMAC signature invalid → 401 | **PASS** |
| 3 | JWT from Tenant A against Tenant B endpoint | Use valid Tenant A token; call `/api/v1/dmas` when tenant context differs | 403 or empty data | `TenantContextMiddleware` sets `search_path` from token slug; Tenant B schema returns empty | **PASS** |
| 4 | Refresh token replay after logout | `POST /auth/logout` then retry with same refresh cookie | 401 Unauthorized | Redis blacklist checked in `POST /auth/refresh` | **PASS** |
| 5 | Brute force (6+ attempts) | POST `/auth/login` 6× with wrong password | 429 on attempt 6 | Redis `INCR` counter; 5-attempt threshold → 429 + 15-min lockout | **PASS** |

---

## RBAC Tests

| # | Test | Method | Expected | Code Path | Result |
|---|------|--------|----------|-----------|--------|
| 6 | `field_viewer` accesses analyst endpoint | `GET /api/v1/leak/indicators` with `field_viewer` token | 403 Forbidden | `require_role(UserRole.analyst)` dependency | **PASS** |
| 7 | `analyst` accesses admin endpoint | `POST /api/v1/tenants` with `analyst` token | 403 Forbidden | `require_role(UserRole.utility_admin)` | **PASS** |
| 8 | `field_viewer` generates worklist | `POST /api/v1/worklist/generate` with `field_viewer` token | 403 Forbidden | `require_role(UserRole.analyst)` on worklist router | **PASS** |

---

## Injection / Input Validation Tests

| # | Test | Method | Expected | Code Path | Result |
|---|------|--------|----------|-----------|--------|
| 9 | CSV formula injection | Upload CSV with cell `=cmd\|'/c calc'` | Cell stored as `'=cmd\|'/c calc'` (prefixed) | `sanitize_csv_cell()` in `core/pii.py` + `_sanitize_dataframe()` | **PASS** |
| 10 | File upload MIME mismatch | Upload `.php` file renamed to `.csv` | 415 Unsupported Media Type | `validate_file_magic()` checks bytes, not extension | **PASS** |
| 11 | PDF path traversal via date param | `POST /reports/water-balance` with `from_date: "../../../etc/passwd"` | 422 Unprocessable Entity | Pydantic `pattern=r"^\d{4}-\d{2}-\d{2}$"` rejects non-date strings | **PASS** |
| 12 | SQL injection in DMA code filter | `GET /api/v1/leak/indicators?dma_code='; DROP TABLE users;--` | 200 with empty results (no error, no damage) | SQLAlchemy parameterized `text(":dma_code")` binding | **PASS** |

---

## Tenant Isolation Tests

| # | Test | Method | Expected | Code Path | Result |
|---|------|--------|----------|-----------|--------|
| 13 | Direct schema query cross-tenant | Tenant A token + raw SQL via API to Tenant B schema | Empty result / 403 | `search_path` set to Tenant A's schema only; no cross-schema access | **PASS** |
| 14 | DMA not in requesting tenant | `GET /api/v1/dmas/{id}` for DMA belonging to another tenant | 404 Not Found | ORM query scoped to tenant schema via `search_path` | **PASS** |

---

## Summary

All 14 checks: **14 PASS / 0 FAIL**

No items requiring remediation before Sprint 9.

---

## Re-test After Any Change To

- `core/security.py` (JWT verification)
- `middleware/tenant.py` (search_path logic)
- Any new router that accepts file uploads or date parameters
- Redis blacklist logic in auth router
