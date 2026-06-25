"""Integration tests for /api/v1/auth endpoints (mocked DB + Redis)."""
from datetime import UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from core.security import hash_password


def _make_user(role="analyst", is_active=True):
    import uuid as _uuid

    from models.user import User
    u = User()
    u.id = _uuid.uuid4()
    u.email = "test@example.ma"
    u.hashed_password = hash_password("correct-password")
    u.role = role
    u.is_active = is_active
    u.tenant_id = _uuid.uuid4()
    u.last_login_at = None
    return u


@pytest.fixture
def auth_client(monkeypatch):
    import os
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://t:t@localhost/t")
    os.environ.setdefault("DATABASE_SYNC_URL", "postgresql+psycopg2://t:t@localhost/t")
    os.environ.setdefault("MINIO_ACCESS_KEY", "t")
    os.environ.setdefault("MINIO_SECRET_KEY", "t")
    os.environ.setdefault("JWT_SECRET", "test-secret-key-for-tests-only-1234")
    os.environ.setdefault("PII_ENCRYPTION_KEY", "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleXQ=")

    # Default mock session — keeps get_db's finally block from hitting a real DB.
    # Individual tests that need custom query results override this with their own patch.
    _mock_session = AsyncMock()
    _mock_session_cls = MagicMock()
    _mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=_mock_session)
    _mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("database.check_db_connection", new_callable=AsyncMock, return_value=True),
        patch("database.AsyncSessionLocal", _mock_session_cls),
        patch("core.storage.create_bucket_if_missing"),
        patch("core.storage.get_storage_client", return_value=MagicMock()),
    ):
        from main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


class TestLogin:
    def test_missing_body_returns_422(self, auth_client):
        resp = auth_client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422

    def test_invalid_credentials_returns_401(self, auth_client):
        user = _make_user()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user

        with (
            patch("routers.auth.check_brute_force", new_callable=AsyncMock),
            patch("routers.auth.record_failed_login", new_callable=AsyncMock),
            patch("database.AsyncSessionLocal") as mock_session_cls,
        ):
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            resp = auth_client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.ma", "password": "wrong-password"},
            )
        assert resp.status_code == 401

    def test_brute_force_returns_429(self, auth_client):
        from fastapi import HTTPException
        with patch(
            "routers.auth.check_brute_force",
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=429, detail="Too many failed attempts"),
        ):
            resp = auth_client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.ma", "password": "any"},
            )
        assert resp.status_code == 429


class TestLogout:
    def test_logout_clears_cookie(self, auth_client):
        resp = auth_client.post("/api/v1/auth/logout")
        assert resp.status_code == 204

    def test_logout_no_auth_required(self, auth_client):
        # Logout should work without any token (clear cookie regardless)
        resp = auth_client.post("/api/v1/auth/logout")
        assert resp.status_code == 204


class TestPasswordReset:
    def test_request_always_returns_202(self, auth_client):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # Email not found

        with patch("database.AsyncSessionLocal") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            resp = auth_client.post(
                "/api/v1/auth/password-reset/request",
                json={"email": "unknown@example.ma"},
            )
        assert resp.status_code == 202

    def test_confirm_invalid_token_returns_400(self, auth_client):
        from datetime import datetime, timedelta
        user = _make_user()
        user.password_reset_token = "valid-token"
        user.password_reset_expires_at = datetime.now(UTC) - timedelta(hours=1)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user

        with patch("database.AsyncSessionLocal") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            resp = auth_client.post(
                "/api/v1/auth/password-reset/confirm",
                json={"token": "valid-token", "new_password": "newpassword123"},
            )
        assert resp.status_code == 400
