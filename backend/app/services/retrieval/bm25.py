"""Keyword search with BM25.

Dense search understands meaning but can miss exact terms: model names ("BERT-large"),
formulas, acronyms, numbers. BM25 scores chunks by how often the query's words appear,
giving rare words more weight and normalising for chunk length.
"""

import re
import threading
from collections import OrderedDict

from rank_bm25 import BM25Okapi
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import Chunk, Document
from app.services.retrieval.dense import ScoredChunk

TOKEN_PATTERN = re.compile(r"[a-z0-9ఀ-౿]+(?:[-.][a-z0-9]+)*")
STOPWORDS = frozenset(
    "a an and are as at be by for from has have how in is it its of on or that the this to was were what "
    "when where which who why will with does did do can could should would about into than then there".split()
)
CACHE_SIZE = 32


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_PATTERN.findall(text.lower()) if t not in STOPWORDS]


class _Index:
    def __init__(self, chunk_ids: list[int], texts: list[str]):
        self.chunk_ids = chunk_ids
        self.bm25 = BM25Okapi([tokenize(text) or ["_"] for text in texts])


_cache: OrderedDict[tuple, _Index] = OrderedDict()
_lock = threading.Lock()


def _scope(user_id: int, document_ids: list[int] | None):
    query = select(Chunk).join(Document).where(Document.user_id == user_id)
    if document_ids:
        query = query.where(Chunk.document_id.in_(document_ids))
    return query


def _get_index(db: Session, user_id: int, document_ids: list[int] | None) -> _Index | None:
    # The index is rebuilt only when the user's chunks change (count or newest id differ).
    scope = _scope(user_id, document_ids).subquery()
    count, max_id = db.execute(select(func.count(), func.max(scope.c.id))).one()
    if not count:
        return None
    key = (user_id, tuple(sorted(document_ids or [])), count, max_id)
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    rows = db.execute(select(scope.c.id, scope.c.text)).all()
    index = _Index([row.id for row in rows], [row.text for row in rows])
    with _lock:
        _cache[key] = index
        if len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return index


def keyword_search(
    db: Session,
    user_id: int,
    query: str,
    top_k: int,
    document_ids: list[int] | None = None,
) -> list[ScoredChunk]:
    terms = tokenize(query)
    index = _get_index(db, user_id, document_ids)
    if not terms or index is None:
        return []
    scores = index.bm25.get_scores(terms)
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    best = [(index.chunk_ids[i], float(scores[i])) for i in ranked if scores[i] > 0]
    chunks = {
        chunk.id: chunk
        for chunk in db.scalars(
            select(Chunk).options(joinedload(Chunk.document)).where(Chunk.id.in_([cid for cid, _ in best]))
        )
    }
    return [ScoredChunk(chunks[cid], score) for cid, score in best if cid in chunks]
