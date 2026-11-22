"""Background job that turns an uploaded PDF into searchable content.

Stages: extract (Module 3) -> later modules add describe figures, chunk and embed.
Runs after the upload request has returned, with its own database session.
"""

import logging
import shutil
import threading
import time
from pathlib import Path

import pymupdf
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.core.clock import utcnow
from app.core.config import settings
from app.models import Document, DocumentElement, DocumentPage, DocumentStatus
from app.services.document_service import document_path
from app.services.indexing import clear_index, index_document
from app.services.multimodal.figures import describe_figures
from app.services.processing.extractor import ExtractionResult, extract_document, guess_title

logger = logging.getLogger(__name__)

# OCR and the ML models use a lot of CPU and RAM, so documents are processed one at a time.
_processing_lock = threading.Lock()


class ProcessingError(Exception):
    """A problem with the document itself. The message is shown to the user."""


def extracted_dir_for(document_id: int) -> Path:
    return settings.extracted_dir / str(document_id)


def process_document(document_id: int, session_factory: sessionmaker[Session]) -> None:
    with _processing_lock, session_factory() as db:
        document = db.get(Document, document_id)
        if document is None:  # deleted before its turn came
            return
        started = time.perf_counter()
        try:
            _run(db, document)
        except ProcessingError as exc:
            _mark_failed(db, document_id, str(exc))
        except Exception:
            logger.exception("Processing document %s failed", document_id)
            _mark_failed(db, document_id, "An unexpected error occurred while processing this document.")
        else:
            elapsed = round(time.perf_counter() - started, 2)
            logger.info("Processed document %s in %ss", document_id, elapsed)
            db.execute(update(Document).where(Document.id == document_id).values(processing_seconds=elapsed))
            db.commit()


def _run(db: Session, document: Document) -> None:
    _set_stage(db, document, "extracting", 2)
    _clear_previous_results(db, document.id)

    pdf_path = document_path(document)
    try:
        pdf = pymupdf.open(pdf_path)
    except (pymupdf.FileDataError, RuntimeError, ValueError):
        raise ProcessingError("The file could not be opened as a PDF. It may be damaged.") from None

    with pdf:
        if pdf.needs_pass:
            raise ProcessingError("Password-protected PDFs are not supported. Remove the password and upload again.")
        if pdf.page_count == 0:
            raise ProcessingError("The PDF has no pages.")
        if pdf.page_count > settings.MAX_PAGES_PER_DOCUMENT:
            raise ProcessingError(f"The PDF has {pdf.page_count} pages; the limit is {settings.MAX_PAGES_PER_DOCUMENT}.")

        document.page_count = pdf.page_count
        document.title = guess_title(pdf)

        def on_progress(done: int, total: int) -> None:
            # Extraction is the first half of the job; commit every few pages, not every page.
            if done == total or done % 5 == 0:
                _set_stage(db, document, "extracting", 2 + int(48 * done / total))

        result = extract_document(pdf, pdf_path, extracted_dir_for(document.id), on_progress)

    _save_extraction(db, document, result)
    notes = list(result.notes)

    # ---------- Describe figures with a vision model (Module 7) ----------
    _set_stage(db, document, "describing", 50)
    notes += describe_figures(
        db, document, lambda done, total: _set_stage(db, document, "describing", 50 + int(10 * done / total))
    )

    # ---------- Chunk + embed + index (Module 4) ----------
    _set_stage(db, document, "chunking", 62)

    def on_embed_progress(done: int, total: int) -> None:
        _set_stage(db, document, "embedding", 65 + int(33 * done / max(total, 1)))

    try:
        chunk_count = index_document(db, document, on_embed_progress)
    except OSError as exc:  # model download failed (offline, disk full, ...)
        logger.exception("Embedding model unavailable")
        raise ProcessingError(f"The embedding model could not be loaded: {exc}") from None
    if chunk_count == 0:
        notes.append("No searchable text was found in this document.")

    document.status = DocumentStatus.READY.value
    document.processing_stage = None
    document.progress = 100
    document.processing_notes = "\n".join(notes) or None
    document.error_message = None
    document.processed_at = utcnow()
    db.commit()


def _save_extraction(db: Session, document: Document, result: ExtractionResult) -> None:
    db.add_all(
        DocumentPage(
            document_id=document.id,
            page_number=page.page_number,
            text=page.text,
            extraction_method=page.method,
            char_count=len(page.text),
            width=page.width,
            height=page.height,
        )
        for page in result.pages
    )
    db.add_all(
        DocumentElement(
            document_id=document.id,
            page_number=element.page_number,
            element_type=element.element_type,
            content=element.content,
            image_path=element.image_path.relative_to(settings.extracted_dir).as_posix() if element.image_path else None,
            bbox=element.bbox,
            extra=element.extra or None,
        )
        for element in result.elements
    )
    document.is_scanned = result.ocr_page_count > len(result.pages) / 2 or any(
        page.method == "ocr_unavailable" for page in result.pages
    )
    db.commit()


def _clear_previous_results(db: Session, document_id: int) -> None:
    """Make reprocessing idempotent: remove anything a previous run produced."""
    clear_index(db, document_id)
    db.execute(delete(DocumentPage).where(DocumentPage.document_id == document_id))
    db.execute(delete(DocumentElement).where(DocumentElement.document_id == document_id))
    db.commit()
    shutil.rmtree(extracted_dir_for(document_id), ignore_errors=True)


def _set_stage(db: Session, document: Document, stage: str, progress: int) -> None:
    document.status = DocumentStatus.PROCESSING.value
    document.processing_stage = stage
    document.progress = progress
    db.commit()


def _mark_failed(db: Session, document_id: int, message: str) -> None:
    db.rollback()
    document = db.get(Document, document_id)
    if document is None:  # deleted while processing
        return
    document.status = DocumentStatus.FAILED.value
    document.processing_stage = None
    document.error_message = message
    db.commit()


def recover_interrupted_jobs(session_factory: sessionmaker[Session]) -> None:
    """A server restart kills running jobs. Mark them failed so the user can reprocess."""
    with session_factory() as db:
        stuck = db.scalars(
            select(Document).where(Document.status.in_([DocumentStatus.PROCESSING.value, DocumentStatus.UPLOADED.value]))
        ).all()
        for document in stuck:
            document.status = DocumentStatus.FAILED.value
            document.processing_stage = None
            document.error_message = "Processing was interrupted by a server restart. Click Reprocess to try again."
        db.commit()
        if stuck:
            logger.warning("Marked %s interrupted document(s) as failed", len(stuck))
