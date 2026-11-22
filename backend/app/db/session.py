from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# The engine manages a pool of reusable connections. It does not connect until first use,
# so the API can still start (and report "degraded") when MySQL is down.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # test a connection before using it; MySQL drops idle ones
    pool_recycle=3600,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session_factory() -> sessionmaker[Session]:
    """FastAPI dependency for background jobs, which outlive the request and need their own sessions.

    Tests override this to point background jobs at the test database.
    """
    return SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request, always closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
