"""Shared test setup.

Tests use an in-memory SQLite database and a temporary upload folder, so they are fast,
need no MySQL, and never touch real data. MySQL-specific behaviour is covered by the
integration tests in Module 11.
"""

import os

# Must run before `app` is imported: settings are read once at import time,
# and real environment variables take priority over backend/.env.
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-at-least-32-characters-long"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["RECOVER_INTERRUPTED_JOBS"] = "false"  # would otherwise touch the real MySQL database
os.environ["PRELOAD_MODELS"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "false"  # enabled explicitly in the rate-limit tests

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import models  # noqa: E402, F401  (registers tables on Base.metadata)
from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db, get_session_factory  # noqa: E402
from app.main import app  # noqa: E402

from app.services.embeddings import encoder  # noqa: E402
from app.services.llm import client as llm_client  # noqa: E402
from app.services.retrieval import reranker  # noqa: E402
from app.services.verification import nli  # noqa: E402
from tests.fakes import FakeEmbedder, FakeLLM, FakeNLI, FakeReranker  # noqa: E402

TEST_PASSWORD = "Str0ngPass!"
REAL_GET_LLM = llm_client.get_llm


@pytest.fixture(autouse=True)
def fake_models(monkeypatch):
    """Every test uses fast fake models instead of downloading real ones or calling Gemini."""
    embedder, fake_reranker, fake_nli = FakeEmbedder(), FakeReranker(), FakeNLI()
    monkeypatch.setattr(encoder, "get_embedder", lambda key=None: embedder)
    monkeypatch.setattr(reranker, "get_reranker", lambda: fake_reranker)
    monkeypatch.setattr(nli, "get_nli_model", lambda: fake_nli)
    monkeypatch.setattr(settings, "FIGURE_DESCRIPTION_DELAY_S", 0)
    monkeypatch.setattr(settings, "RELEVANCE_THRESHOLD", 0.3)
    return embedder


@pytest.fixture(autouse=True)
def fake_llm(monkeypatch):
    llm = FakeLLM()
    monkeypatch.setattr(llm_client, "get_llm", lambda: llm)
    return llm


@pytest.fixture
def session_factory():
    # StaticPool keeps one connection, so every session sees the same in-memory database.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")  # SQLite ignores FKs unless asked

    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def client(session_factory, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path)

    def _get_test_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_test_db
    app.dependency_overrides[get_session_factory] = lambda: session_factory  # background jobs
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(client):
    """Register + log in a user and return the Authorization header for them."""

    def _make(email: str = "asha@example.com", password: str = TEST_PASSWORD) -> dict[str, str]:
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "full_name": "Test User", "password": password},
        )
        response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _make
