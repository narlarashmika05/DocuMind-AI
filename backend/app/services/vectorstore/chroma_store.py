"""ChromaDB wrapper. One collection per embedding model, because vectors from different
models live in different spaces and cannot be compared with each other.

Every vector carries user_id and document_id metadata. Every query filters on user_id,
so one user's search can never return another user's passages.
"""

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class VectorHit:
    chunk_id: int
    similarity: float  # cosine similarity, 1.0 = identical direction
    metadata: dict[str, Any]


class VectorStore:
    def __init__(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(path), settings=ChromaSettings(anonymized_telemetry=False, allow_reset=False)
        )

    def _collection(self, model_key: str):
        # HNSW = the approximate nearest-neighbour index; cosine distance suits normalized embeddings.
        return self.client.get_or_create_collection(f"chunks_{model_key}", metadata={"hnsw:space": "cosine"})

    def add(
        self,
        model_key: str,
        chunk_ids: list[int],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        if chunk_ids:
            self._collection(model_key).upsert(
                ids=[str(i) for i in chunk_ids], embeddings=embeddings, metadatas=metadatas
            )

    def query(
        self,
        model_key: str,
        embedding: list[float],
        n_results: int,
        user_id: int,
        document_ids: list[int] | None = None,
    ) -> list[VectorHit]:
        collection = self._collection(model_key)
        total = collection.count()
        if total == 0:
            return []
        where: dict[str, Any] = {"user_id": user_id}
        if document_ids:
            where = {"$and": [where, {"document_id": {"$in": document_ids}}]}
        result = collection.query(
            query_embeddings=[embedding],
            n_results=min(n_results, total),
            where=where,
            include=["metadatas", "distances"],
        )
        return [
            VectorHit(int(chunk_id), 1.0 - distance, metadata)
            for chunk_id, distance, metadata in zip(result["ids"][0], result["distances"][0], result["metadatas"][0])
        ]

    def delete_document(self, document_id: int) -> None:
        for collection in self.client.list_collections():
            # Chroma 0.5 returns Collection objects, 0.6+ returns names; accept both.
            name = collection if isinstance(collection, str) else collection.name
            self.client.get_collection(name).delete(where={"document_id": document_id})


_stores: dict[Path, VectorStore] = {}
_lock = threading.Lock()


def get_vector_store() -> VectorStore:
    path = settings.chroma_dir
    with _lock:
        if path not in _stores:
            _stores[path] = VectorStore(path)
        return _stores[path]
