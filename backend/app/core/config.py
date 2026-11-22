from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

BACKEND_DIR = Path(__file__).resolve().parents[2]
# backend/.env, resolved from this file so it works no matter where uvicorn is started
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """All configuration comes from environment variables or backend/.env.

    Real environment variables take priority over the .env file, which is how
    Docker and cloud platforms will inject secrets later (Module 12).
    """

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "DocuMind AI"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "documind_user"
    MYSQL_PASSWORD: str = ""
    MYSQL_DB: str = "documind"

    # Comma-separated, e.g. "http://localhost:5173,http://127.0.0.1:5173"
    CORS_ORIGINS: str = "http://localhost:5173"

    # ---------- Authentication ----------
    # Required, with no default on purpose: the app refuses to start without a real secret.
    JWT_SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ---------- File uploads ----------
    STORAGE_DIR: Path = BACKEND_DIR / "storage"
    MAX_UPLOAD_SIZE_MB: int = 25
    MAX_FILES_PER_UPLOAD: int = 10

    # ---------- Document processing (Module 3) ----------
    MAX_PAGES_PER_DOCUMENT: int = 500
    # A page with less native text than this, mostly covered by an image, is treated as scanned.
    MIN_TEXT_CHARS_PER_PAGE: int = 40
    OCR_LANGUAGES: str = "eng"  # "eng+tel" once Telugu language data is installed
    OCR_DPI: int = 300
    TESSERACT_CMD: str | None = None  # full path to tesseract.exe if it is not on PATH
    MIN_IMAGE_SIZE_PX: int = 120  # smaller images are usually icons or logos
    MAX_IMAGES_PER_DOCUMENT: int = 40
    # ---------- Security (Module 11) ----------
    RATE_LIMIT_ENABLED: bool = True

    # Mark jobs that were cut off by a server restart as failed on startup.
    RECOVER_INTERRUPTED_JOBS: bool = True

    # ---------- Chunking and embeddings (Module 4) ----------
    # Key from app/services/embeddings/registry.py
    EMBEDDING_MODEL: str = "multilingual-e5-base"
    CHUNK_STRATEGY: str = "recursive"  # fixed | recursive | sentence (LlamaIndex)
    CHUNK_SIZE_TOKENS: int = 300
    CHUNK_OVERLAP_TOKENS: int = 50
    SKIP_REFERENCES_SECTION: bool = True  # bibliography text pollutes search results
    EMBEDDING_BATCH_SIZE: int = 16
    # Load the embedding model in the background at startup, so the first upload is not slow.
    PRELOAD_MODELS: bool = True

    # ---------- Retrieval (Modules 4-5) ----------
    RETRIEVAL_CANDIDATES: int = 20  # chunks fetched by each search before fusion/reranking
    RRF_K: int = 60  # Reciprocal Rank Fusion constant (60 is the value from the original paper)
    # English cross-encoder (90 MB). Telugu questions are reranked using their English translation.
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # ---------- LLM: Gemini (Module 5) ----------
    # Secret: only ever in backend/.env, never in frontend code or Git.
    GEMINI_API_KEY: str | None = None
    # Check https://ai.google.dev/gemini-api/docs/models for current model names.
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TEMPERATURE: float = 0.2  # low = factual and consistent
    GEMINI_MAX_OUTPUT_TOKENS: int = 4096
    LLM_MAX_RETRIES: int = 2

    # ---------- RAG (Module 5) ----------
    RAG_TOP_K: int = 5  # passages given to the LLM
    # Minimum reranker probability for a passage to count as relevant. If no passage
    # reaches it, the assistant says it does not have enough information (no LLM call).
    # 0.05 chosen from the evaluation (Module 9): on the benchmark every unanswerable question
    # scored < 0.01 and every answerable one > 0.05; 0.15 wrongly refused 3% of answerable queries.
    RELEVANCE_THRESHOLD: float = 0.05
    HISTORY_TURNS: int = 3  # previous question/answer pairs used for follow-up questions

    # ---------- Multimodal (Module 7) ----------
    DESCRIBE_FIGURES: bool = True  # Gemini vision describes extracted figures during processing
    MAX_FIGURES_TO_DESCRIBE: int = 15  # per document; protects the free-tier quota
    FIGURE_DESCRIPTION_DELAY_S: float = 4.0  # pause between vision calls (free tier: ~15 requests/min)
    MAX_IMAGES_PER_ANSWER: int = 3

    # ---------- Answer verification (Module 8) ----------
    NLI_MODEL: str = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
    SUPPORTED_THRESHOLD: float = 0.7  # entailment probability for "supported"
    PARTIAL_THRESHOLD: float = 0.35  # ... for "partially supported"
    CONTRADICTION_THRESHOLD: float = 0.7

    # ---------- Evaluation results (Module 9) ----------
    EVALUATION_RESULTS_DIR: Path = BACKEND_DIR.parent / "evaluation" / "results"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def upload_dir(self) -> Path:
        return self.STORAGE_DIR / "uploads"

    @property
    def extracted_dir(self) -> Path:
        return self.STORAGE_DIR / "extracted"

    @property
    def chroma_dir(self) -> Path:
        return self.STORAGE_DIR / "chroma"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def database_url(self) -> URL:
        # URL.create escapes special characters in the password (e.g. "@" or "#"),
        # which would otherwise break a hand-written connection string.
        return URL.create(
            drivername="mysql+pymysql",
            username=self.MYSQL_USER,
            password=self.MYSQL_PASSWORD,
            host=self.MYSQL_HOST,
            port=self.MYSQL_PORT,
            database=self.MYSQL_DB,
            query={"charset": "utf8mb4"},  # full Unicode, required for Telugu text
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
