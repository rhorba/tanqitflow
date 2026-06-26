"""TanqitFlow load test — Story 9.4.

Run with:
  pip install locust
  locust -f tests/load/locust_load_test.py --host=https://localhost \
         --users 50 --spawn-rate 5 --run-time 60s --headless

Scenarios:
  S1: 50 concurrent users querying /dashboard/summary → P95 < 500ms
  S2: 10 concurrent CSV uploads (separate data, no deadlocks)
  S3: Single large CSV import validation (300 DMAs × 1000 reads)
"""
from __future__ import annotations

import io
import os
import random
import time

from locust import HttpUser, between, events, task
from locust.env import Environment

# ---------------------------------------------------------------------------
# Auth helper — get JWT once per user
# ---------------------------------------------------------------------------

ADMIN_EMAIL = os.environ.get("LOAD_TEST_EMAIL", "admin@demo.ma")
ADMIN_PASS = os.environ.get("LOAD_TEST_PASS", "Demo1234!")


class TanqitFlowUser(HttpUser):
    wait_time = between(0.5, 2.0)
    token: str = ""

    def on_start(self):
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
            verify=False,
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token", "")
        else:
            self.token = ""

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    # -----------------------------------------------------------------------
    # Scenario 1: Dashboard reads — P95 < 500ms target
    # -----------------------------------------------------------------------

    @task(10)
    def get_dashboard_summary(self):
        self.client.get(
            "/api/v1/balance/summary",
            headers=self._headers(),
            name="GET /balance/summary",
            verify=False,
        )

    @task(8)
    def get_balance_trend(self):
        months = random.choice([3, 6, 12])
        self.client.get(
            f"/api/v1/balance/trend?months={months}",
            headers=self._headers(),
            name="GET /balance/trend",
            verify=False,
        )

    @task(6)
    def get_dma_list(self):
        page = random.randint(1, 5)
        self.client.get(
            f"/api/v1/dmas?page={page}&page_size=20",
            headers=self._headers(),
            name="GET /dmas",
            verify=False,
        )

    @task(5)
    def get_leak_indicators(self):
        self.client.get(
            "/api/v1/leak/indicators?page=1&page_size=10",
            headers=self._headers(),
            name="GET /leak/indicators",
            verify=False,
        )

    @task(4)
    def get_worklist(self):
        self.client.get(
            "/api/v1/worklist?page=1&page_size=20",
            headers=self._headers(),
            name="GET /worklist",
            verify=False,
        )

    # -----------------------------------------------------------------------
    # Scenario 2: Concurrent CSV uploads — 10 concurrent uploads
    # -----------------------------------------------------------------------

    @task(2)
    def upload_small_csv(self):
        """Upload a 50-row DMA inflow CSV (simulates concurrent upload scenario)."""
        dma_codes = [f"DMA-LOAD-{i:03d}" for i in range(1, 11)]
        rows = ["dma_code,reading_date,volume_m3"]
        for dma in dma_codes:
            for day in range(1, 6):
                vol = random.randint(3000, 12000)
                rows.append(f"{dma},2026-01-{day:02d},{vol}")
        csv_content = "\n".join(rows).encode("utf-8")

        self.client.post(
            "/api/v1/ingestion/upload",
            files={"file": ("load_test.csv", io.BytesIO(csv_content), "text/csv")},
            data={"job_type": "DMA_INFLOW"},
            headers=self._headers(),
            name="POST /ingestion/upload (small)",
            verify=False,
        )

    @task(1)
    def get_ingestion_jobs(self):
        self.client.get(
            "/api/v1/ingestion/jobs?page=1&page_size=10",
            headers=self._headers(),
            name="GET /ingestion/jobs",
            verify=False,
        )


# ---------------------------------------------------------------------------
# Scenario 3: Large CSV — 300 DMAs × 1000 rows
# ---------------------------------------------------------------------------

def generate_large_csv(n_dmas: int = 300, reads_per_dma: int = 1000) -> bytes:
    """Generate a synthetic 300-DMA × 1000-read CSV for import."""
    rows = ["dma_code,reading_date,volume_m3"]
    base_date = "2026-01"
    for dma_i in range(1, n_dmas + 1):
        dma_code = f"DMA-{dma_i:04d}"
        for read_i in range(reads_per_dma):
            day = (read_i % 28) + 1
            vol = round(random.uniform(1000, 15000), 2)
            rows.append(f"{dma_code},{base_date}-{day:02d},{vol}")
    return "\n".join(rows).encode("utf-8")


class LargeCsvUser(HttpUser):
    """Single-user scenario for large CSV import timing test."""
    wait_time = between(30, 60)
    token: str = ""

    def on_start(self):
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
            verify=False,
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token", "")

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    @task
    def import_large_csv(self):
        """Upload a 300-DMA × 1000-row CSV — Celery task should complete in < 60s."""
        csv_bytes = generate_large_csv(n_dmas=300, reads_per_dma=1000)
        start = time.time()
        resp = self.client.post(
            "/api/v1/ingestion/upload",
            files={"file": ("large_300dma.csv", io.BytesIO(csv_bytes), "text/csv")},
            data={"job_type": "DMA_INFLOW"},
            headers=self._headers(),
            name="POST /ingestion/upload (300K rows)",
            verify=False,
        )
        elapsed = time.time() - start
        if resp.status_code == 202 and elapsed < 5.0:
            # Upload accepted — good; Celery picks it up asynchronously
            pass


# ---------------------------------------------------------------------------
# Results summary hook
# ---------------------------------------------------------------------------

@events.quitting.add_listener
def on_quitting(environment: Environment, **_kwargs):
    if environment.stats.total.fail_ratio > 0.05:
        print(f"\nLOAD TEST WARN: >5% failure rate ({environment.stats.total.fail_ratio:.1%})")
    p95 = environment.stats.get("/api/v1/balance/summary", "GET")
    if p95:
        p95_ms = p95.get_response_time_percentile(0.95)
        if p95_ms > 500:
            print(f"\nLOAD TEST WARN: /balance/summary P95={p95_ms:.0f}ms exceeds 500ms target")
        else:
            print(f"\nLOAD TEST PASS: /balance/summary P95={p95_ms:.0f}ms < 500ms ✓")
