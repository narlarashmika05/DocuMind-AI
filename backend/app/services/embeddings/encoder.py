import logging
import threading
from typing import Protocol

from app.core.config import settings
from app.services.embeddings.registry import EmbeddingModelSpec, get_spec

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    spec: EmbeddingModelSpec

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...

    def count_tokens(self, text: str) -> int: ...

    def tokenize(self, text: str) -> list[int]: ...


class SentenceTransformerEmbedder:
    def __init__(self, spec: EmbeddingModelSpec):
        from sentence_transformers import SentenceTransformer  # heavy import (PyTorch), load lazily

        logger.info("Loading embedding model %s (first time downloads ~%s MB)", spec.hf_name, spec.size_mb)
        self.spec = spec
        self.model = SentenceTransformer(spec.hf_name, device="cpu")
        self.model.max_seq_length = min(spec.max_tokens, 512)

    def _encode(self, texts: list[str]) -> list[list[float]]:
        # normalize_embeddings=True makes every vector length 1, so cosine similarity = dot product.
        vectors = self.model.encode(
            texts,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return vectors.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode([self.spec.passage_prefix + text for text in texts])

    def embed_query(self, text: str) -> list[float]:
        return self._encode([self.spec.query_prefix + text])[0]

    def tokenize(self, text: str) -> list[int]:
        return self.model.tokenizer.encode(text, add_special_tokens=False)

    def count_tokens(self, text: str) -> int:
        return len(self.tokenize(text))


_embedders: dict[str, Embedder] = {}
_lock = threading.Lock()


def get_embedder(key: str | None = None) -> Embedder:
    """Load each model once per process (loading takes seconds and ~1 GB of RAM)."""
    key = key or settings.EMBEDDING_MODEL
    with _lock:
        if key not in _embedders:
            _embedders[key] = SentenceTransformerEmbedder(get_spec(key))
        return _embedders[key]
