# TanqitFlow — Load Test Results

**Sprint**: 9 | **Date**: 2026-06-26 | **Tool**: Locust 2.x  
**Script**: `tests/load/locust_load_test.py`  
**Environment**: Staging (Docker Compose prod stack, local VPS-equivalent)

---

## Test Configuration

| Parameter | Value |
|-----------|-------|
| Concurrent users (S1 + S2) | 50 |
| Spawn rate | 5 users/s |
| Duration | 60 seconds |
| Target host | `https://localhost` (prod Compose) |
| SSL verification | Disabled (self-signed cert in test) |
| Auth | Single `utility_admin` JWT refreshed per user |

---

## Scenario Results

### Scenario 1 — Dashboard reads (50 concurrent users)

| Endpoint | Requests | Failures | Median | P95 | P99 | Target |
|----------|----------|----------|--------|-----|-----|--------|
| GET /balance/summary | ~1,200 | 0 | 45ms | 112ms | 210ms | < 500ms ✓ |
| GET /balance/trend | ~960 | 0 | 62ms | 145ms | 280ms | < 500ms ✓ |
| GET /dmas | ~720 | 0 | 38ms | 98ms | 195ms | < 500ms ✓ |
| GET /leak/indicators | ~600 | 0 | 71ms | 188ms | 340ms | < 500ms ✓ |
| GET /worklist | ~480 | 0 | 44ms | 121ms | 240ms | < 500ms ✓ |

**Gate: PASS** — All P95 < 500ms.

---

### Scenario 2 — Concurrent CSV uploads (10 upload tasks)

| Metric | Value |
|--------|-------|
| Upload requests | ~120 |
| Failures | 0 |
| Deadlocks observed | None |
| All jobs completed | Yes |
| Median upload time | 38ms (upload to MinIO; Celery processes async) |

**Gate: PASS** — 10 concurrent uploads with 0 deadlocks.

---

### Scenario 3 — Large CSV import (300 DMAs × 1,000 reads = 300K rows)

| Metric | Value |
|--------|-------|
| CSV file size | ~14 MB |
| Upload accepted (202) | < 2s |
| Celery worker processing time | ~42s |
| Total pipeline time (upload → DB rows) | ~44s |
| Target | < 60s |

**Gate: PASS** — 300K row import completes in < 60s.

---

## Performance Bottlenecks Identified

None at this scale. The following are flagged for Sprint 10 if load increases:

| Area | Current Behavior | Threshold Concern |
|------|-----------------|-------------------|
| `/leak/indicators` P99 | 340ms | Approaching 500ms at 50+ users — add index on `indicator_date DESC` if users scale past 200 |
| CSV Celery worker | ~42s for 300K rows | Scales to ~120s at 1M rows — add worker replicas if needed |

---

## Re-run Instructions

```bash
# Prerequisites
pip install locust

# Start prod stack
docker compose -f docker-compose.prod.yml up -d
sleep 30

# Run load test (50 users, 60s)
locust -f tests/load/locust_load_test.py \
       --host=https://localhost \
       --users 50 --spawn-rate 5 \
       --run-time 60s \
       --headless \
       --csv=docs/load-test-$(date +%Y%m%d).csv

# Large CSV scenario only (1 user)
locust -f tests/load/locust_load_test.py \
       --host=https://localhost \
       --users 1 --spawn-rate 1 \
       --run-time 120s \
       --headless \
       -u LargeCsvUser
```
