from unittest.mock import AsyncMock, MagicMock, patch


class TestHealthEndpoint:
    def test_all_services_healthy(self, client):
        with (
            patch("routers.health.check_db_connection", new_callable=AsyncMock, return_value=True),
            patch("routers.health.aioredis.from_url") as mock_redis,
            patch("routers.health.get_storage_client") as mock_storage,
        ):
            mock_redis.return_value.__aenter__ = AsyncMock()
            mock_redis_instance = AsyncMock()
            mock_redis_instance.ping = AsyncMock()
            mock_redis_instance.aclose = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            mock_storage.return_value = MagicMock()

            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_db_unhealthy_returns_degraded(self, client):
        with (
            patch("routers.health.check_db_connection", new_callable=AsyncMock, return_value=False),
            patch("routers.health.aioredis.from_url") as mock_redis,
            patch("routers.health.get_storage_client") as mock_storage,
        ):
            mock_redis_instance = AsyncMock()
            mock_redis_instance.ping = AsyncMock()
            mock_redis_instance.aclose = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            mock_storage.return_value = MagicMock()

            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["db"] == "error"

    def test_redis_unhealthy_returns_degraded(self, client):
        with (
            patch("routers.health.check_db_connection", new_callable=AsyncMock, return_value=True),
            patch("routers.health.aioredis.from_url") as mock_redis,
            patch("routers.health.get_storage_client") as mock_storage,
        ):
            mock_redis_instance = AsyncMock()
            mock_redis_instance.ping.side_effect = Exception("Connection refused")
            mock_redis_instance.aclose = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            mock_storage.return_value = MagicMock()

            response = client.get("/health")

        data = response.json()
        assert data["status"] == "degraded"
        assert data["redis"] == "error"

    def test_minio_unhealthy_returns_degraded(self, client):
        with (
            patch("routers.health.check_db_connection", new_callable=AsyncMock, return_value=True),
            patch("routers.health.aioredis.from_url") as mock_redis,
            patch("routers.health.get_storage_client") as mock_storage,
        ):
            mock_redis_instance = AsyncMock()
            mock_redis_instance.ping = AsyncMock()
            mock_redis_instance.aclose = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            mock_storage.return_value.list_buckets.side_effect = Exception("MinIO down")

            response = client.get("/health")

        data = response.json()
        assert data["status"] == "degraded"
        assert data["minio"] == "error"

    def test_health_response_has_all_keys(self, client):
        with (
            patch("routers.health.check_db_connection", new_callable=AsyncMock, return_value=True),
            patch("routers.health.aioredis.from_url") as mock_redis,
            patch("routers.health.get_storage_client") as mock_storage,
        ):
            mock_redis_instance = AsyncMock()
            mock_redis_instance.ping = AsyncMock()
            mock_redis_instance.aclose = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            mock_storage.return_value = MagicMock()

            response = client.get("/health")

        data = response.json()
        assert set(data.keys()) == {"status", "db", "redis", "minio"}
