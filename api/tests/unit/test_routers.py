"""Unit tests for routers using FastAPI dependency overrides (no real DB)."""
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://t:t@localhost/t")
os.environ.setdefault("DATABASE_SYNC_URL", "postgresql+psycopg2://t:t@localhost/t")
os.environ.setdefault("MINIO_ACCESS_KEY", "t")
os.environ.setdefault("MINIO_SECRET_KEY", "t")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-tests-only-1234")
os.environ.setdefault("PII_ENCRYPTION_KEY", "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleXQ=")


def _mock_user(role: str = "utility_admin") -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.email = "admin@example.ma"
    u.role = role
    u.is_active = True
    u.tenant_id = uuid.uuid4()
    return u


def _mock_db() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def app_client():
    with (
        patch("database.check_db_connection", new_callable=AsyncMock, return_value=True),
        patch("core.storage.create_bucket_if_missing"),
        patch("core.storage.get_storage_client", return_value=MagicMock()),
    ):
        from core.security import get_current_user, require_role
        from database import get_db
        from main import app
        from models.user import UserRole

        mock_user = _mock_user("utility_admin")
        mock_db = _mock_db()

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user
        for role in UserRole:
            app.dependency_overrides[require_role(role)] = lambda: mock_user

        with TestClient(app, raise_server_exceptions=False) as c:
            yield c, mock_user, mock_db

        app.dependency_overrides.clear()


class TestAuthRouter:
    def test_login_missing_fields_returns_422(self, app_client):
        client, _, _ = app_client
        resp = client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422

    def test_login_invalid_email_returns_422(self, app_client):
        client, _, _ = app_client
        resp = client.post("/api/v1/auth/login", json={"email": "not-an-email", "password": "x"})
        assert resp.status_code == 422

    def test_logout_returns_204(self, app_client):
        client, _, _ = app_client
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 204

    def test_password_reset_request_missing_email_returns_422(self, app_client):
        client, _, _ = app_client
        resp = client.post("/api/v1/auth/password-reset/request", json={})
        assert resp.status_code == 422


class TestDMARouter:
    def test_list_dmas_calls_db(self, app_client):
        client, _, mock_db = app_client
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        resp = client.get("/api/v1/dmas")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "meta" in data
        assert data["data"] == []

    def test_get_dma_not_found_returns_404(self, app_client):
        client, _, mock_db = app_client
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        resp = client.get(f"/api/v1/dmas/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_create_dma_conflict_returns_409(self, app_client):
        client, _, mock_db = app_client
        # Simulate existing DMA
        existing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute = AsyncMock(return_value=mock_result)

        resp = client.post(
            "/api/v1/dmas",
            json={"code": "DMA001", "name": "Zone Nord"},
        )
        assert resp.status_code == 409

    def test_create_dma_invalid_body_returns_422(self, app_client):
        client, _, _ = app_client
        resp = client.post("/api/v1/dmas", json={})
        assert resp.status_code == 422


class TestUserRouter:
    def test_list_users_calls_db(self, app_client):
        client, mock_user, mock_db = app_client
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        resp = client.get("/api/v1/users")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_user_not_found_returns_404(self, app_client):
        client, _, mock_db = app_client
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        resp = client.get(f"/api/v1/users/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_create_user_conflict_returns_409(self, app_client):
        client, _, mock_db = app_client
        existing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute = AsyncMock(return_value=mock_result)

        resp = client.post(
            "/api/v1/users",
            json={"email": "exists@example.ma", "password": "password123"},
        )
        assert resp.status_code == 409


class TestIngestionRouter:
    def test_list_jobs_calls_db(self, app_client):
        client, _, mock_db = app_client
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        resp = client.get("/api/v1/ingestion/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert data["data"] == []

    def test_get_job_not_found_returns_404(self, app_client):
        client, _, mock_db = app_client
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        resp = client.get(f"/api/v1/ingestion/jobs/{uuid.uuid4()}")
        assert resp.status_code == 404
