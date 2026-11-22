"""API tests for /api/v1/health.

The database is replaced with a fake session, so these tests run without MySQL.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db.session import get_db
from app.main import app

client = TestClient(app)


class FakeSession:
    def __init__(self, fail: bool):
        self.fail = fail

    def execute(self, *args, **kwargs):
        if self.fail:
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    def close(self):
        pass


@pytest.fixture
def use_database():
    """Swap the real database for a fake one; call with fail=True to simulate an outage."""

    def _apply(fail: bool = False):
        def _get_fake_db():
            yield FakeSession(fail)

        app.dependency_overrides[get_db] = _get_fake_db

    yield _apply
    app.dependency_overrides.clear()


def test_health_ok_when_database_connected(use_database):
    use_database(fail=False)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
    assert body["database_latency_ms"] is not None


def test_health_degraded_when_database_down(use_database):
    use_database(fail=True)

    response = client.get("/api/v1/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == "unavailable"


def test_cors_allows_frontend_origin():
    response = client.options(
        "/api/v1/health",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )

    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_rejects_unknown_origin():
    response = client.options(
        "/api/v1/health",
        headers={"Origin": "http://evil.example.com", "Access-Control-Request-Method": "GET"},
    )

    assert "access-control-allow-origin" not in response.headers
