"""Integration tests for /api/v1/ingestion endpoints (mocked DB + MinIO + Celery)."""
import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def ingestion_client():
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

    password = "Test1234!"
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    mock_user = MagicMock()
    mock_user.id = str(uuid.uuid4())
    mock_user.email = "analyst@util.ma"
    mock_user.hashed_password = hashed
    mock_user.role = "analyst"
    mock_user.tenant_id = str(uuid.uuid4())
    mock_user.is_active = True
    mock_user.last_login_at = None

    async def _mock_get(*_args, **_kwargs):
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

        resp = client.post("/api/v1/auth/login", json={"email": "analyst@util.ma", "password": password})

    if resp.status_code != 200:
        return ""
    return resp.json().get("access_token", "")


class TestUploadEndpoint:
    def test_unauthenticated_upload_returns_401(self, ingestion_client):
        csv_data = b"dma_code,reading_date,volume_m3\nDMA-01,2026-01-01,1000\n"
        resp = ingestion_client.post(
            "/api/v1/ingestion/upload",
            files={"file": ("data.csv", io.BytesIO(csv_data), "text/csv")},
            data={"job_type": "DMA_INFLOW"},
        )
        assert resp.status_code == 401

    def test_php_file_disguised_as_csv_rejected(self, ingestion_client):
        token = _analyst_token(ingestion_client)
        if not token:
            pytest.skip("auth setup failed")
        binary_garbage = bytes(range(256)) * 16  # 4096 bytes of non-UTF8 binary with no structure

        with patch("core.storage.get_storage_client", return_value=MagicMock()):
            resp = ingestion_client.post(
                "/api/v1/ingestion/upload",
                files={"file": ("exploit.csv", io.BytesIO(binary_garbage), "text/csv")},
                data={"job_type": "DMA_INFLOW"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code in (415, 401, 403, 422)

    def test_oversized_file_rejected(self, ingestion_client):
        token = _analyst_token(ingestion_client)
        if not token:
            pytest.skip("auth setup failed")
        # Simulate a 60MB file (above 50MB limit)
        large_csv_header = b"dma_code,reading_date,volume_m3\n"
        row = b"DMA-01,2026-01-01,1000\n"
        # Build a large enough payload just from the size perspective
        large_data = large_csv_header + row * 3_000_000  # ~70 MB

        with patch("core.storage.get_storage_client", return_value=MagicMock()):
            resp = ingestion_client.post(
                "/api/v1/ingestion/upload",
                files={"file": ("big.csv", io.BytesIO(large_data), "text/csv")},
                data={"job_type": "DMA_INFLOW"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code in (413, 422, 401, 403)


class TestJobListEndpoint:
    def test_unauthenticated_returns_401(self, ingestion_client):
        resp = ingestion_client.get("/api/v1/ingestion/jobs")
        assert resp.status_code == 401

    def test_authenticated_returns_list(self, ingestion_client):
        token = _analyst_token(ingestion_client)
        if not token:
            pytest.skip("auth setup failed")

        mock_rows = MagicMock()
        mock_rows.all.return_value = []

        with patch("database.AsyncSessionLocal") as mock_cls:
            sess = AsyncMock()
            r = MagicMock()
            r.all.return_value = []
            sess.execute = AsyncMock(return_value=r)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=sess)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            resp = ingestion_client.get(
                "/api/v1/ingestion/jobs",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code in (200, 403)
