import logging
import time

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check(response: Response, db: Session = Depends(get_db)) -> HealthResponse:
    """Report whether the API and its database are working.

    Returns 200 when healthy and 503 when the database is unreachable, so load
    balancers and Docker health checks can react to the status code alone.
    """
    database = "connected"
    latency_ms = None

    start = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
    except SQLAlchemyError as exc:
        logger.warning("Database health check failed: %s", exc)
        database = "unavailable"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status="ok" if database == "connected" else "degraded",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        database=database,
        database_latency_ms=latency_ms,
    )
