"""Unit tests for services/tenant.py."""
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://t:t@localhost/t")
os.environ.setdefault("DATABASE_SYNC_URL", "postgresql+psycopg2://t:t@localhost/t")
os.environ.setdefault("MINIO_ACCESS_KEY", "t")
os.environ.setdefault("MINIO_SECRET_KEY", "t")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-tests-only-1234")
os.environ.setdefault("PII_ENCRYPTION_KEY", "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleXQ=")


class TestProvisionTenant:
    async def test_invalid_slug_raises_value_error(self):
        from services.tenant import provision_tenant
        with pytest.raises(ValueError, match="Invalid tenant slug"):
            await provision_tenant("INVALID SLUG!", MagicMock())

    async def test_slug_with_spaces_raises(self):
        from services.tenant import provision_tenant
        with pytest.raises(ValueError):
            await provision_tenant("my tenant", MagicMock())

    async def test_slug_too_short_raises(self):
        from services.tenant import provision_tenant
        with pytest.raises(ValueError):
            await provision_tenant("a", MagicMock())

    async def test_valid_slug_creates_schema_and_tables(self):
        from services.tenant import provision_tenant

        executed = []
        mock_db = AsyncMock()
        async def capture(stmt, *a, **kw):
            executed.append(str(stmt))
        mock_db.execute = capture

        mock_s3 = MagicMock()
        mock_s3.put_object = MagicMock()

        with patch("services.tenant.get_storage_client", return_value=mock_s3):
            await provision_tenant("util_rabat", mock_db)

        # Schema creation ran
        assert any("util_rabat" in s for s in executed)
        # MinIO prefix created
        mock_s3.put_object.assert_called_once()
        call_kwargs = mock_s3.put_object.call_args.kwargs
        assert "util_rabat/.keep" in call_kwargs["Key"]

    async def test_minio_failure_does_not_raise(self):
        """MinIO prefix creation is best-effort; failure is logged but not raised."""
        from services.tenant import provision_tenant

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()

        mock_s3 = MagicMock()
        mock_s3.put_object = MagicMock(side_effect=Exception("MinIO down"))

        with patch("services.tenant.get_storage_client", return_value=mock_s3):
            # Should NOT raise
            await provision_tenant("util_casablanca", mock_db)


class TestBruteForce:
    async def test_check_brute_force_passes_when_below_limit(self):
        from core.security import check_brute_force

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="3")
        mock_redis.aclose = AsyncMock()

        with patch("core.security._get_redis", return_value=mock_redis):
            await check_brute_force("user@example.ma")  # should not raise

    async def test_check_brute_force_raises_429_when_limit_exceeded(self):
        from fastapi import HTTPException

        from core.security import check_brute_force

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="5")
        mock_redis.aclose = AsyncMock()

        with patch("core.security._get_redis", return_value=mock_redis):
            with pytest.raises(HTTPException) as exc_info:
                await check_brute_force("user@example.ma")
            assert exc_info.value.status_code == 429

    async def test_check_brute_force_passes_when_no_key(self):
        from core.security import check_brute_force

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.aclose = AsyncMock()

        with patch("core.security._get_redis", return_value=mock_redis):
            await check_brute_force("new@example.ma")  # should not raise

    async def test_record_failed_login_increments_counter(self):
        from core.security import record_failed_login

        mock_pipe = AsyncMock()
        mock_pipe.execute = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        mock_redis.aclose = AsyncMock()

        with patch("core.security._get_redis", return_value=mock_redis):
            await record_failed_login("bad@example.ma")

        mock_pipe.incr.assert_awaited_once()
        mock_pipe.expire.assert_awaited_once()

    async def test_clear_brute_force_deletes_key(self):
        from core.security import clear_brute_force

        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock()
        mock_redis.aclose = AsyncMock()

        with patch("core.security._get_redis", return_value=mock_redis):
            await clear_brute_force("good@example.ma")

        mock_redis.delete.assert_awaited_once_with("bf:good@example.ma")
