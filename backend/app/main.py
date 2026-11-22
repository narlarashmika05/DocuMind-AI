import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.router import api_router
from app.core import middleware
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.embeddings.encoder import get_embedder
from app.services.processing.pipeline import recover_interrupted_jobs
from app.services.retrieval.reranker import get_reranker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("documind")


def _preload_models() -> None:
    try:
        get_embedder()
        get_reranker()
        logger.info("Models loaded")
    except Exception:
        logger.exception("Preloading models failed; they will be loaded on first use")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code before `yield` runs once at startup; code after it runs at shutdown.
    # Later modules load ML models here so they are not reloaded on every request.
    logger.info("Starting %s v%s (%s)", settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.extracted_dir.mkdir(parents=True, exist_ok=True)
    if settings.RECOVER_INTERRUPTED_JOBS:
        try:
            recover_interrupted_jobs(SessionLocal)
        except SQLAlchemyError as exc:  # the API should still start if MySQL is down
            logger.warning("Could not check for interrupted jobs: %s", exc)
    if settings.PRELOAD_MODELS:
        # Load models in a background thread: the API is usable immediately, and the first
        # upload or question does not wait ~30 s for the models to load.
        threading.Thread(target=_preload_models, name="preload-models", daemon=True).start()
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Multimodal, multilingual and hallucination-aware research assistant API.",
    lifespan=lifespan,
)

# The browser blocks calls from http://localhost:5173 (React) to http://localhost:8000 (API)
# unless the API explicitly allows that origin. Only listed origins are allowed, never "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

middleware.install(app)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"message": f"{settings.APP_NAME} API is running", "docs": "/docs"}
