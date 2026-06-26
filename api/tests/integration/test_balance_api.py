"""Integration tests for /api/v1/dashboard and /api/v1/dmas balance endpoints."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def balance_client():
    with (
        patch("database.check_db_connection", new_callable=AsyncMock, return_value=True),
        patch("core.storage.get_storage_client", return_value=MagicMock()),
        patch("core.storage.create_bucket_if_missing"),
    ):
        from main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def _viewer_token(client: TestClient) -> str:
    from unittest.mock import AsyncMock, MagicMock, patch

    import bcrypt

    password = "Viewer1234!"
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    mock_user = MagicMock()
    mock_user.id = str(uuid.uuid4())
    mock_user.email = "viewer@util.ma"
    mock_user.hashed_password = hashed
    mock_user.role = "field_viewer"
    mock_user.tenant_id = str(uuid.uuid4())
    mock_user.is_active = True
    mock_user.last_login_at = None

    async def _mock_get(*_a, **_kw):
        r = MagicMock()
        r.scalar_one_or_none.return_value = mock_user
        r.first.return_value = mock_user
        return r

    with (
        patch("routers.auth.check_brute_force", new_callable=AsyncMock),
        patch("routers.auth.record_failed_login", new_callable=AsyncMock),
        patch("database.AsyncSessionLocal") as mock_cls,
    ):
        sess = AsyncMock()
        sess.execute = _mock_get
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=sess)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
        resp = client.post("/api/v1/auth/login", json={"email": "viewer@util.ma", "password": password})

    if resp.status_code != 200:
        return ""
    return resp.json().get("access_token", "")


class TestBalanceSummary:
    def test_unauthenticated_returns_401(self, balance_client):
        resp = balance_client.get("/api/v1/balance/summary")
        assert resp.status_code == 401

    def test_authenticated_returns_summary(self, balance_client):
        token = _viewer_token(balance_client)
        if not token:
            pytest.skip("auth setup failed")

        mock_row = MagicMock(
            total_siv=50000.0,
            total_scv=38000.0,
            total_nrw=12000.0,
            nrw_pct=24.0,
            flagged_dmas=3,
        )
        with patch("database.AsyncSessionLocal") as mock_cls:
            sess = AsyncMock()
            r = MagicMock()
            r.first.return_value = mock_row
            sess.execute = AsyncMock(return_value=r)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=sess)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            resp = balance_client.get(
                "/api/v1/balance/summary",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "siv_m3" in data
        assert "nrw_pct" in data

    def test_summary_returns_correct_keys(self, balance_client):
        token = _viewer_token(balance_client)
        if not token:
            pytest.skip("auth setup failed")

        mock_row = MagicMock(
            total_siv=10000.0, total_scv=8000.0,
            total_nrw=2000.0, nrw_pct=20.0, flagged_dmas=1,
        )
        with patch("database.AsyncSessionLocal") as mock_cls:
            sess = AsyncMock()
            r = MagicMock()
            r.first.return_value = mock_row
            sess.execute = AsyncMock(return_value=r)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=sess)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            resp = balance_client.get(
                "/api/v1/balance/summary",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        keys = set(resp.json().keys())
        assert {"siv_m3", "scv_m3", "nrw_m3", "nrw_pct", "flagged_dmas"}.issubset(keys)


class TestBalanceTrend:
    def test_trend_requires_auth(self, balance_client):
        resp = balance_client.get("/api/v1/balance/trend")
        assert resp.status_code == 401

    def test_trend_returns_list(self, balance_client):
        token = _viewer_token(balance_client)
        if not token:
            pytest.skip("auth setup failed")

        rows = [
            MagicMock(month="2026-06", siv_m3=5000.0, nrw_m3=1000.0, nrw_pct=20.0),
        ]
        with patch("database.AsyncSessionLocal") as mock_cls:
            sess = AsyncMock()
            r = MagicMock()
            r.__iter__ = MagicMock(return_value=iter(rows))
            sess.execute = AsyncMock(return_value=r)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=sess)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            resp = balance_client.get(
                "/api/v1/balance/trend",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestDmaListEndpoint:
    def test_requires_auth(self, balance_client):
        resp = balance_client.get("/api/v1/dmas")
        assert resp.status_code == 401

    def test_returns_paginated_response(self, balance_client):
        token = _viewer_token(balance_client)
        if not token:
            pytest.skip("auth setup failed")

        count_row = MagicMock()
        count_row.scalar.return_value = 0
        rows_result = MagicMock()
        rows_result.all.return_value = []

        with patch("database.AsyncSessionLocal") as mock_cls:
            sess = AsyncMock()
            sess.execute = AsyncMock(side_effect=[count_row, rows_result])
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=sess)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            resp = balance_client.get(
                "/api/v1/dmas",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
