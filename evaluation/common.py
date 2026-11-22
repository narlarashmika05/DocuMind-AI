"""Shared helpers: import the backend, load datasets, and build in-memory search indexes.

The evaluation reuses the application's own extraction, chunking, embedding, BM25,
fusion and reranking code, but keeps everything in memory, so it never touches the
MySQL database, ChromaDB or any user's documents.
"""

import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
DATASETS = ROOT / "datasets"
CORPUS_DIR = DATASETS / "corpus"
RESULTS_DIR = ROOT / "results"

sys.path.insert(0, str(REPO_ROOT / "backend"))
# Evaluation does not use authentication; a placeholder lets the settings load without backend/.env.
os.environ.setdefault("JWT_SECRET_KEY", "evaluation-only-placeholder-secret-0000000000")

import numpy as np  # noqa: E402
import pymupdf  # noqa: E402
from rank_bm25 import BM25Okapi  # noqa: E402

from app.services.chunking.chunker import ElementInput, PageInput, chunk_document  # noqa: E402
from app.services.indexing import embedding_text  # noqa: E402
from app.services.processing.extractor import extract_document, guess_title  # noqa: E402
from app.services.retrieval.bm25 import tokenize  # noqa: E402
from app.services.retrieval.dense import ScoredChunk  # noqa: E402
from app.services.retrieval.retriever import reciprocal_rank_fusion  # noqa: E402


def load_jsonl(name: str) -> list[dict]:
    with open(DATASETS / name, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


@dataclass
class EvalChunk:
    id: int
    document: str
    page: int
    text: str
    element_type: str

    @property
    def page_key(self) -> tuple[str, int]:
        return (self.document, self.page)


@dataclass
class ExtractedDoc:
    file: str
    title: str
    pages: list[PageInput]
    elements: list[ElementInput]


def extract_corpus() -> list[ExtractedDoc]:
    if not any(CORPUS_DIR.glob("*.pdf")):
        raise SystemExit("No corpus PDFs found. Run: python evaluation/build_corpus.py")
    docs, element_id = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        for path in sorted(CORPUS_DIR.glob("*.pdf")):
            with pymupdf.open(path) as pdf:
                result = extract_document(pdf, path, Path(tmp) / path.stem)
                title = guess_title(pdf) or path.stem
            elements = []
            for element in result.elements:
                element_id += 1
                elements.append(ElementInput(element_id, element.page_number, element.element_type, element.content))
            pages = [PageInput(p.page_number, p.text) for p in result.pages]
            docs.append(ExtractedDoc(path.name, title, pages, elements))
    return docs


class EvalIndex:
    """Dense + BM25 index over the corpus for one (embedding model, chunking strategy)."""

    def __init__(self, docs: list[ExtractedDoc], embedder, strategy: str, size: int, overlap: int):
        self.embedder = embedder
        self.chunks: list[EvalChunk] = []
        texts = []
        for doc in docs:
            drafts = chunk_document(
                doc.pages,
                doc.elements,
                strategy=strategy,
                count=embedder.count_tokens,
                tokenize=embedder.tokenize,
                size=min(size, embedder.spec.max_tokens - 32),  # same cap as indexing.effective_chunk_size
                overlap=overlap,
            )
            for draft in drafts:
                self.chunks.append(EvalChunk(len(self.chunks) + 1, doc.file, draft.page_number, draft.text, draft.element_type))
                texts.append(embedding_text(doc.title, draft.text))
        started = time.perf_counter()
        self.vectors = np.asarray(embedder.embed_documents(texts), dtype=np.float32)
        self.index_seconds = time.perf_counter() - started
        self.bm25 = BM25Okapi([tokenize(c.text) or ["_"] for c in self.chunks])

    def _dense(self, query: str, n: int) -> list[ScoredChunk]:
        # Exact cosine search (vectors are normalised). ChromaDB's HNSW is approximate,
        # but on a corpus this small the results are effectively identical.
        scores = self.vectors @ np.asarray(self.embedder.embed_query(query), dtype=np.float32)
        order = np.argsort(-scores)[:n]
        return [ScoredChunk(self.chunks[i], float(scores[i])) for i in order]

    def _keyword(self, query: str, n: int) -> list[ScoredChunk]:
        terms = tokenize(query)
        if not terms:
            return []
        scores = self.bm25.get_scores(terms)
        order = np.argsort(-scores)[:n]
        return [ScoredChunk(self.chunks[i], float(scores[i])) for i in order if scores[i] > 0]

    def search(
        self,
        query: str,
        english_query: str,
        mode: str,
        reranker=None,
        top_k: int = 10,
        candidates: int = 20,
    ) -> list[ScoredChunk]:
        """Same logic as app.services.retrieval.retriever.retrieve, in memory."""
        lists = []
        if mode in ("dense", "hybrid"):
            lists.append(self._dense(query, candidates))
        if mode in ("keyword", "hybrid"):
            lists.append(self._keyword(english_query, candidates))
        results = reciprocal_rank_fusion(lists) if mode == "hybrid" else lists[0]
        results = results[:candidates]
        if reranker and results:
            scores = reranker.score(english_query, [r.chunk.text for r in results])
            results = sorted(
                (ScoredChunk(r.chunk, s) for r, s in zip(results, scores)), key=lambda r: r.score, reverse=True
            )
        return results[:top_k]


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H-%M-%S")


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
