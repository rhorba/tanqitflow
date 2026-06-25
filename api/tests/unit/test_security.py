"""Unit tests for JWT creation/verification and RBAC."""
import pytest
from jose import jwt
from unittest.mock import AsyncMock, MagicMock, patch

import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("DATABASE_SYNC_URL", "postgresql+psycopg2://test:test@localhost/test")
os.environ.setdefault("MINIO_ACCESS_KEY", "test")
os.environ.setdefault("MINIO_SECRET_KEY", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-tests-only-1234")
os.environ.setdefault("PII_ENCRYPTION_KEY", "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleXQ=")


from core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from config import get_settings

settings = get_settings()


class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = hash_password("mysecret123")
        assert verify_password("mysecret123", hashed)
        assert not verify_password("wrong", hashed)

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt salts


class TestAccessToken:
    def test_create_and_decode(self):
        token = create_access_token("user-123", "tenant_abc", "analyst")
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["tenant_slug"] == "tenant_abc"
        assert payload["role"] == "analyst"
        assert payload["type"] == "access"

    def test_expired_token_raises(self):
        from datetime import timedelta
        from unittest.mock import patch
        import time

        # Patch settings to expire immediately
        with patch("core.security.settings") as mock_settings:
            mock_settings.jwt_secret = settings.jwt_secret
            mock_settings.jwt_algorithm = settings.jwt_algorithm
            mock_settings.jwt_access_token_expire_minutes = 0
            mock_settings.jwt_refresh_token_expire_days = 0
            token = create_access_token("u", "t", "analyst")

        import time; time.sleep(1)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == 401

    def test_tampered_token_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            decode_token("not.a.valid.token")


class TestRefreshToken:
    def test_type_is_refresh(self):
        token = create_refresh_token("user-456", "tenant_xyz")
        payload = decode_token(token)
        assert payload["type"] == "refresh"
        assert payload["sub"] == "user-456"
        assert payload["tenant_slug"] == "tenant_xyz"
        assert "role" not in payload


class TestRequireRole:
    def test_role_constants(self):
        from models.user import UserRole
        assert UserRole.utility_admin.value == "utility_admin"
        assert UserRole.analyst.value == "analyst"
        assert UserRole.field_viewer.value == "field_viewer"
