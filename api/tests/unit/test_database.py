"""Unit tests for database helpers."""
import os
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://t:t@localhost/t")
os.environ.setdefault("DATABASE_SYNC_URL", "postgresql+psycopg2://t:t@localhost/t")
os.environ.setdefault("MINIO_ACCESS_KEY", "t")
os.environ.setdefault("MINIO_SECRET_KEY", "t")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-tests-only-1234")
os.environ.setdefault("PII_ENCRYPTION_KEY", "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleXQ=")


class TestCheckDbConnection:
    async def test_returns_true_when_query_succeeds(self):
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("database.AsyncSessionLocal", return_value=mock_ctx):
            from database import check_db_connection
            result = await check_db_connection()
        assert result is True

    async def test_returns_false_when_query_fails(self):
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(side_effect=Exception("connection refused"))
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("database.AsyncSessionLocal", return_value=mock_ctx):
            from database import check_db_connection
            result = await check_db_connection()
        assert result is False


class TestGetDb:
    async def test_sets_search_path_when_tenant_present(self):
        executed_statements = []

        mock_session = AsyncMock()
        async def capture_execute(stmt, *args, **kwargs):
            executed_statements.append(str(stmt))
            return MagicMock()
        mock_session.execute = capture_execute
        mock_session.commit = AsyncMock()

        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        from database import current_tenant_slug, get_db
        token = current_tenant_slug.set("test_tenant")
        try:
            with patch("database.AsyncSessionLocal", return_value=mock_ctx):
                async for session in get_db():
                    pass  # just exhaust the generator
        finally:
            current_tenant_slug.reset(token)

        assert any("test_tenant" in s for s in executed_statements)

    async def test_no_tenant_specific_search_path_when_no_tenant(self):
        executed_statements = []

        mock_session = AsyncMock()
        async def capture_execute(stmt, *args, **kwargs):
            executed_statements.append(str(stmt))
            return MagicMock()
        mock_session.execute = capture_execute
        mock_session.commit = AsyncMock()

        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        from database import current_tenant_slug, get_db
        token = current_tenant_slug.set(None)
        try:
            with patch("database.AsyncSessionLocal", return_value=mock_ctx):
                async for _session in get_db():
                    pass
        finally:
            current_tenant_slug.reset(token)

        # Only the finally-block reset should run (no tenant-specific schema routing)
        assert not any(", public" in s for s in executed_statements)
