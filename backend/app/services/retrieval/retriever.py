"""Retrieval orchestration: dense, keyword or hybrid search, optionally reranked."""

from collections import defaultdict
from dataclasses import replace

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.retrieval import bm25, dense, reranker
from app.services.retrieval.dense import ScoredChunk

MODES = ("dense", "keyword", "hybrid")


def reciprocal_rank_fusion(result_lists: list[list[ScoredChunk]], k: int = 60) -> list[ScoredChunk]:
    """Merge rankings from different searches.

    Dense similarities (0-1) and BM25 scores (0-30+) are on different scales, so we
    ignore the raw scores and use only each chunk's *rank*: score = sum of 1 / (k + rank).
    A chunk ranked well by both searches beats one ranked well by only one.
    """
    fused: dict[int, float] = defaultdict(float)
    chunks = {}
    for results in result_lists:
        for rank, item in enumerate(results, start=1):
            fused[item.chunk.id] += 1.0 / (k + rank)
            chunks[item.chunk.id] = item.chunk
    order = sorted(fused, key=fused.get, reverse=True)
    return [ScoredChunk(chunks[chunk_id], fused[chunk_id]) for chunk_id in order]


def retrieve(
    db: Session,
    user_id: int,
    query: str,
    *,
    top_k: int = 5,
    mode: str = "hybrid",
    rerank: bool = True,
    document_ids: list[int] | None = None,
    english_query: str | None = None,
) -> list[ScoredChunk]:
    """Return the top_k most relevant chunks.

    `english_query` is the question translated to English (Module 6). Dense search uses
    the original question because the embedding model is multilingual; BM25 and the
    reranker are English-only, so they use the translation.
    """
    if mode not in MODES:
        raise ValueError(f"Unknown retrieval mode '{mode}'")
    english_query = english_query or query
    candidates = max(settings.RETRIEVAL_CANDIDATES, top_k)

    result_lists = []
    if mode in ("dense", "hybrid"):
        result_lists.append(dense.dense_search(db, user_id, query, candidates, document_ids))
    if mode in ("keyword", "hybrid"):
        result_lists.append(bm25.keyword_search(db, user_id, english_query, candidates, document_ids))

    results = reciprocal_rank_fusion(result_lists, settings.RRF_K) if mode == "hybrid" else result_lists[0]
    results = results[:candidates]

    if rerank and results:
        scores = reranker.get_reranker().score(english_query, [item.chunk.text for item in results])
        results = sorted(
            (replace(item, score=score) for item, score in zip(results, scores)), key=lambda r: r.score, reverse=True
        )
    return results[:top_k]
