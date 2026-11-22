"""Semantic (dense) search: embed the question and find the nearest chunk vectors."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Chunk, Document
from app.services.embeddings import encoder
from app.services.vectorstore.chroma_store import get_vector_store


@dataclass
class ScoredChunk:
    chunk: Chunk
    score: float


def load_user_chunks(db: Session, user_id: int, chunk_ids: list[int]) -> dict[int, Chunk]:
    """Fetch chunks by id, re-checking ownership in SQL (defence in depth on top of the vector filter)."""
    if not chunk_ids:
        return {}
    rows = db.scalars(
        select(Chunk)
        .join(Document)
        .options(joinedload(Chunk.document))
        .where(Chunk.id.in_(chunk_ids), Document.user_id == user_id)
    )
    return {chunk.id: chunk for chunk in rows}


def dense_search(
    db: Session,
    user_id: int,
    query: str,
    top_k: int,
    document_ids: list[int] | None = None,
) -> list[ScoredChunk]:
    embedder = encoder.get_embedder()
    hits = get_vector_store().query(embedder.spec.key, embedder.embed_query(query), top_k, user_id, document_ids)
    chunks = load_user_chunks(db, user_id, [hit.chunk_id for hit in hits])
    # Hits whose chunk no longer exists (deleted document) are skipped.
    return [ScoredChunk(chunks[hit.chunk_id], hit.similarity) for hit in hits if hit.chunk_id in chunks]
