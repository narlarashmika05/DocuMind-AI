"""Cross-encoder reranking.

The embedding model (a bi-encoder) encodes the question and each chunk separately,
which is fast but approximate. A cross-encoder reads the question and the chunk
*together* and outputs a relevance probability - much more accurate, but too slow to
run on every chunk. So: retrieve ~20 candidates cheaply, then rerank only those.
"""

import logging
import threading
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)


class Reranker(Protocol):
    def score(self, query: str, texts: list[str]) -> list[float]: ...


class CrossEncoderReranker:
    def __init__(self, model_name: str):
        import torch
        from sentence_transformers import CrossEncoder

        logger.info("Loading reranker %s", model_name)
        self.model = CrossEncoder(model_name, max_length=512, device="cpu")
        self._sigmoid = torch.nn.Sigmoid()

    def score(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        # Sigmoid turns the raw score into a 0-1 relevance probability (used by the relevance gate).
        scores = self.model.predict(
            [(query, text) for text in texts], activation_fct=self._sigmoid, show_progress_bar=False
        )
        return [float(s) for s in scores]


_reranker: Reranker | None = None
_lock = threading.Lock()


def get_reranker() -> Reranker:
    global _reranker
    with _lock:
        if _reranker is None:
            _reranker = CrossEncoderReranker(settings.RERANKER_MODEL)
        return _reranker
