import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Set minimal env vars before importing app modules
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/tanqitflow_test")
os.environ.setdefault("DATABASE_SYNC_URL", "postgresql+psycopg2://test:test@localhost:5432/tanqitflow_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "testkey")
os.environ.setdefault("MINIO_SECRET_KEY", "testsecret")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-tests-only")
os.environ.setdefault("PII_ENCRYPTION_KEY", "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleXQ=")


@pytest.fixture
def mock_settings():
    from config import get_settings
    return get_settings()


@pytest.fixture
def client():
    """FastAPI test client with mocked dependencies."""
    with (
        patch("database.check_db_connection", new_callable=AsyncMock, return_value=True),
        patch("core.storage.get_storage_client") as mock_storage,
        patch("core.storage.create_bucket_if_missing"),
    ):
        mock_storage.return_value = MagicMock()
        from main import app
        with TestClient(app) as c:
            yield c
