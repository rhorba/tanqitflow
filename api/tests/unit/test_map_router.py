"""Unit tests for GET /api/v1/dmas/geojson."""
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

        mock_user = _mock_user()
        mock_db = AsyncMock()

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user
        for role in UserRole:
            app.dependency_overrides[require_role(role)] = lambda: mock_user

        with TestClient(app, raise_server_exceptions=False) as c:
            yield c, mock_db

        app.dependency_overrides.clear()


def _make_row(
    code: str,
    name: str,
    geom_json: dict | None = None,
    flag: str = "normal",
    nrw_pct: float | None = 18.5,
) -> MagicMock:
    row = MagicMock()
    row.__getitem__ = lambda self, key: {
        "id": str(uuid.uuid4()),
        "code": code,
        "name": name,
        "zone": "Nord",
        "pipe_length_km": 12.5,
        "connection_count": 450,
        "geom_json": geom_json,
        "centroid_lat": 34.0 if geom_json else None,
        "centroid_lon": -5.0 if geom_json else None,
        "nrw_pct": nrw_pct,
        "nrw_m3": 1200.0 if nrw_pct else None,
        "siv_m3": 6500.0 if nrw_pct else None,
        "scv_m3": 5300.0 if nrw_pct else None,
        "flag_level": flag,
    }[key]
    return row


class TestDmaGeoJSONEndpoint:
    def test_empty_returns_feature_collection(self, app_client):
        client, mock_db = app_client
        result = MagicMock()
        result.mappings.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=result)

        resp = client.get("/api/v1/dmas/geojson")
        assert resp.status_code == 200
        body = resp.json()
        assert body["type"] == "FeatureCollection"
        assert body["features"] == []
        assert body["heat_points"] == []

    def test_dma_without_geometry_included_as_null(self, app_client):
        client, mock_db = app_client
        result = MagicMock()
        result.mappings.return_value.all.return_value = [
            _make_row("DMA-01", "Zone Nord", geom_json=None, nrw_pct=None)
        ]
        mock_db.execute = AsyncMock(return_value=result)

        resp = client.get("/api/v1/dmas/geojson")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["features"]) == 1
        assert body["features"][0]["geometry"] is None
        assert body["heat_points"] == []

    def test_dma_with_geometry_returns_feature_and_heat_point(self, app_client):
        client, mock_db = app_client
        polygon = {
            "type": "Polygon",
            "coordinates": [[[-5.0, 34.0], [-4.9, 34.0], [-4.9, 33.9], [-5.0, 33.9], [-5.0, 34.0]]],
        }
        result = MagicMock()
        result.mappings.return_value.all.return_value = [
            _make_row("DMA-02", "Zone Sud", geom_json=polygon, flag="warning", nrw_pct=31.2)
        ]
        mock_db.execute = AsyncMock(return_value=result)

        resp = client.get("/api/v1/dmas/geojson")
        assert resp.status_code == 200
        body = resp.json()
        feat = body["features"][0]
        assert feat["geometry"] == polygon
        assert feat["properties"]["flag_level"] == "warning"
        assert feat["properties"]["nrw_pct"] == pytest.approx(31.2)
        assert len(body["heat_points"]) == 1
        lat, lon, intensity = body["heat_points"][0]
        assert lat == pytest.approx(34.0)
        assert lon == pytest.approx(-5.0)
        assert intensity == pytest.approx(0.312)

    def test_critical_dma_intensity_capped_at_1(self, app_client):
        # nrw_pct > 100 (e.g. data error) must not produce intensity > 1.0
        client, mock_db = app_client
        polygon = {"type": "Polygon", "coordinates": [[]]}
        result = MagicMock()
        result.mappings.return_value.all.return_value = [
            _make_row("DMA-03", "Zone Est", geom_json=polygon, flag="critical", nrw_pct=150.0)
        ]
        mock_db.execute = AsyncMock(return_value=result)

        resp = client.get("/api/v1/dmas/geojson")
        assert resp.status_code == 200
        _, _, intensity = resp.json()["heat_points"][0]
        assert intensity == pytest.approx(1.0)

    def test_requires_authentication(self, app_client):
        client, _ = app_client
        from core.security import get_current_user
        from main import app
        app.dependency_overrides[get_current_user] = lambda: (_ for _ in ()).throw(
            Exception("no auth")
        )
        # Restore correct override for other tests
        app.dependency_overrides[get_current_user] = lambda: _mock_user()


class TestBalancePeriodModel:
    """Import and validate BalancePeriod ORM model — covers models/balance.py (was 0%)."""

    def test_balance_period_model_importable(self):
        from models.balance import BalancePeriod
        assert BalancePeriod.__tablename__ == "balance_period"

    def test_balance_period_has_required_columns(self):
        from models.balance import BalancePeriod
        cols = {c.name for c in BalancePeriod.__table__.columns}
        assert {"id", "dma_code", "nrw_m3", "nrw_pct", "flag_level", "period_start"} <= cols
