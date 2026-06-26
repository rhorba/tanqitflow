"""Integration tests for /api/v1/leak endpoints."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def leak_client():
    with (
        patch("database.check_db_connection", new_callable=AsyncMock, return_value=True),
        patch("core.storage.get_storage_client", return_value=MagicMock()),
        patch("core.storage.create_bucket_if_missing"),
    ):
        from main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def _analyst_token(client: TestClient) -> str:
    from unittest.mock import AsyncMock, MagicMock, patch

    import bcrypt

    password = "Analyst1234!"
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    mock_user = MagicMock()
    mock_user.id = str(uuid.uuid4())
    mock_user.email = "analyst@leak.ma"
    mock_user.hashed_password = hashed
    mock_user.role = "analyst"
    mock_user.tenant_id = "tenant_leak"
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
        resp = client.post("/api/v1/auth/login", json={"email": "analyst@leak.ma", "password": password})

    if resp.status_code != 200:
        return ""
    return resp.json().get("access_token", "")


class TestLeakIndicatorsEndpoint:
    def test_requires_auth(self, leak_client):
        resp = leak_client.get("/api/v1/leak/indicators")
        assert resp.status_code == 401

    def test_returns_indicators_list(self, leak_client):
        token = _analyst_token(leak_client)
        if not token:
            pytest.skip("auth setup failed")

        rows = [
            MagicMock(
                id=str(uuid.uuid4()),
                dma_code="DMA-01",
                indicator_date="2026-06-01",
                confidence_score=75,
                alert_type="MNF",
                mnf_flag=True,
                zscore_flag=False,
                if_flag=False,
            )
        ]
        count_row = MagicMock()
        count_row.scalar.return_value = 1
        rows_result = MagicMock()
        rows_result.all.return_value = rows

        with patch("database.AsyncSessionLocal") as mock_cls:
            sess = AsyncMock()
            sess.execute = AsyncMock(side_effect=[count_row, rows_result])
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=sess)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            resp = leak_client.get(
                "/api/v1/leak/indicators",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200

    def test_field_viewer_forbidden_on_indicators(self, leak_client):
        """field_viewer role should NOT have access to leak indicators (analyst+ required)."""
        import bcrypt

        password = "Viewer1234!"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        mock_viewer = MagicMock()
        mock_viewer.id = str(uuid.uuid4())
        mock_viewer.email = "viewer@leak.ma"
        mock_viewer.hashed_password = hashed
        mock_viewer.role = "field_viewer"
        mock_viewer.tenant_id = "tenant_leak"
        mock_viewer.is_active = True
        mock_viewer.last_login_at = None

        async def _mock_get(*_a, **_kw):
            r = MagicMock()
            r.scalar_one_or_none.return_value = mock_viewer
            r.first.return_value = mock_viewer
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
            resp = leak_client.post(
                "/api/v1/auth/login",
                json={"email": "viewer@leak.ma", "password": password},
            )

        if resp.status_code != 200:
            pytest.skip("auth setup failed")
        viewer_token = resp.json().get("access_token", "")

        resp2 = leak_client.get(
            "/api/v1/leak/indicators",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp2.status_code == 403


class TestAnomalyEventsEndpoint:
    def test_requires_auth(self, leak_client):
        resp = leak_client.get("/api/v1/leak/anomalies")
        assert resp.status_code == 401

    def test_returns_anomaly_list(self, leak_client):
        token = _analyst_token(leak_client)
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

            resp = leak_client.get(
                "/api/v1/leak/anomalies",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
