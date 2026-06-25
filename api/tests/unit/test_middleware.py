"""Unit tests for TenantContextMiddleware and AuditLogMiddleware helpers."""
import os

from jose import jwt
from starlette.requests import Request
from starlette.responses import Response
from starlette.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://t:t@localhost/t")
os.environ.setdefault("DATABASE_SYNC_URL", "postgresql+psycopg2://t:t@localhost/t")
os.environ.setdefault("MINIO_ACCESS_KEY", "t")
os.environ.setdefault("MINIO_SECRET_KEY", "t")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-tests-only-1234")
os.environ.setdefault("PII_ENCRYPTION_KEY", "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleXQ=")

from config import get_settings
from middleware.audit import _extract_user_info
from middleware.tenant import TenantContextMiddleware, _extract_bearer

settings = get_settings()


class TestExtractBearer:
    def test_no_auth_header_returns_none(self):
        scope = {"type": "http", "method": "GET", "path": "/", "headers": []}
        request = Request(scope)
        assert _extract_bearer(request) is None

    def test_bearer_token_extracted(self):
        token = "abc.def.ghi"
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"authorization", f"Bearer {token}".encode())],
        }
        request = Request(scope)
        assert _extract_bearer(request) == token

    def test_non_bearer_scheme_returns_none(self):
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"authorization", b"Basic dXNlcjpwYXNz")],
        }
        request = Request(scope)
        assert _extract_bearer(request) is None

    def test_empty_auth_header_returns_none(self):
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"authorization", b"")],
        }
        request = Request(scope)
        assert _extract_bearer(request) is None


class TestExtractUserInfo:
    def _make_token(self, sub: str, email: str) -> str:
        from datetime import UTC, datetime, timedelta
        payload = {
            "sub": sub,
            "email": email,
            "type": "access",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=15),
            "jti": "test-jti",
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    def test_no_auth_returns_none_tuple(self):
        scope = {"type": "http", "method": "POST", "path": "/", "headers": []}
        request = Request(scope)
        user_id, email = _extract_user_info(request)
        assert user_id is None
        assert email is None

    def test_valid_jwt_returns_user_info(self):
        token = self._make_token("user-uuid-123", "admin@example.ma")
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": [(b"authorization", f"Bearer {token}".encode())],
        }
        request = Request(scope)
        user_id, email = _extract_user_info(request)
        assert user_id == "user-uuid-123"
        assert email == "admin@example.ma"

    def test_tampered_jwt_returns_none_tuple(self):
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": [(b"authorization", b"Bearer not.a.valid.token")],
        }
        request = Request(scope)
        user_id, email = _extract_user_info(request)
        assert user_id is None
        assert email is None


class TestTenantContextMiddleware:
    def _make_client(self):
        from starlette.applications import Starlette
        from starlette.routing import Route

        async def homepage(request: Request) -> Response:
            from database import current_tenant_slug
            slug = current_tenant_slug.get()
            return Response(slug or "none")

        app = Starlette(routes=[Route("/protected", homepage), Route("/health", homepage)])
        app.add_middleware(TenantContextMiddleware)
        return TestClient(app, raise_server_exceptions=False)

    def test_public_path_no_tenant_set(self):
        client = self._make_client()
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.text == "none"

    def test_protected_path_without_token_passes_through(self):
        client = self._make_client()
        resp = client.get("/protected")
        assert resp.status_code == 200
        assert resp.text == "none"

    def test_protected_path_with_valid_jwt_sets_tenant(self):
        from datetime import UTC, datetime, timedelta
        payload = {
            "sub": "user-1",
            "tenant_slug": "util_rabat",
            "type": "access",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=15),
            "jti": "jti-1",
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        client = self._make_client()
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.text == "util_rabat"

    def test_malformed_jwt_does_not_crash(self):
        client = self._make_client()
        resp = client.get("/protected", headers={"Authorization": "Bearer garbage.token.here"})
        assert resp.status_code == 200  # middleware swallows bad JWTs, lets route handle 401
