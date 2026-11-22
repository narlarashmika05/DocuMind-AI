"""Chunk a processed document, embed the chunks and store the vectors (Module 4)."""

import logging
from collections.abc import Callable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Chunk, Document, DocumentElement, DocumentPage
from app.services.chunking.chunker import ChunkDraft, ElementInput, PageInput, chunk_document
from app.services.embeddings import encoder
from app.services.vectorstore.chroma_store import get_vector_store

logger = logging.getLogger(__name__)


def effective_chunk_size(max_tokens: int) -> int:
    # Leave room for the "passage: " prefix and the title line added before embedding;
    # anything past the model's limit would be silently cut off.
    return min(settings.CHUNK_SIZE_TOKENS, max_tokens - 32)


def embedding_text(title: str, chunk_text: str) -> str:
    # Adding the document title gives every chunk context ("which paper is this from?").
    return f"{title}\n{chunk_text}"


def clear_index(db: Session, document_id: int) -> None:
    db.execute(delete(Chunk).where(Chunk.document_id == document_id))
    db.commit()
    get_vector_store().delete_document(document_id)


def build_chunks(db: Session, document: Document) -> list[ChunkDraft]:
    embedder = encoder.get_embedder()
    pages = [
        PageInput(page.page_number, page.text)
        for page in db.scalars(
            select(DocumentPage).where(DocumentPage.document_id == document.id).order_by(DocumentPage.page_number)
        )
    ]
    elements = [
        ElementInput(element.id, element.page_number, element.element_type, element.content)
        for element in db.scalars(select(DocumentElement).where(DocumentElement.document_id == document.id))
    ]
    return chunk_document(
        pages,
        elements,
        strategy=settings.CHUNK_STRATEGY,
        count=embedder.count_tokens,
        tokenize=embedder.tokenize,
        size=effective_chunk_size(embedder.spec.max_tokens),
        overlap=settings.CHUNK_OVERLAP_TOKENS,
        skip_references=settings.SKIP_REFERENCES_SECTION,
    )


def index_document(db: Session, document: Document, on_progress: Callable[[int, int], None] | None = None) -> int:
    """Returns the number of chunks indexed."""
    clear_index(db, document.id)
    embedder = encoder.get_embedder()
    drafts = build_chunks(db, document)

    chunks = [
        Chunk(
            document_id=document.id,
            page_number=draft.page_number,
            chunk_index=index,
            element_type=draft.element_type,
            element_id=draft.element_id,
            text=draft.text,
            token_count=draft.token_count,
        )
        for index, draft in enumerate(drafts)
    ]
    db.add_all(chunks)
    db.flush()  # assigns chunk ids, used as vector ids in ChromaDB

    store = get_vector_store()
    title = document.title or document.original_filename
    batch_size = settings.EMBEDDING_BATCH_SIZE * 4
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        vectors = embedder.embed_documents([embedding_text(title, chunk.text) for chunk in batch])
        store.add(
            embedder.spec.key,
            [chunk.id for chunk in batch],
            vectors,
            [
                {
                    "user_id": document.user_id,
                    "document_id": document.id,
                    "page_number": chunk.page_number,
                    "element_type": chunk.element_type,
                }
                for chunk in batch
            ],
        )
        if on_progress:
            on_progress(min(start + batch_size, len(chunks)), len(chunks))

    document.embedding_model = embedder.spec.key
    document.chunk_strategy = settings.CHUNK_STRATEGY
    document.chunk_count = len(chunks)
    db.commit()
    logger.info("Indexed document %s: %s chunks with %s", document.id, len(chunks), embedder.spec.key)
    return len(chunks)
