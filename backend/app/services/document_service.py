import hashlib
import logging
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Document
from app.services.security.file_validator import FileRejected, check_active_content, sanitize_filename, validate_pdf
from app.services.vectorstore.chroma_store import get_vector_store

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1024 * 1024  # read uploads 1 MB at a time instead of loading them into memory


def document_path(document: Document) -> Path:
    # Each user has their own folder; the file name is a random UUID.
    return settings.upload_dir / str(document.user_id) / document.stored_filename


def save_upload(db: Session, user_id: int, upload: UploadFile) -> Document:
    """Validate, store and register one uploaded PDF. Raises FileRejected on any problem."""
    filename = sanitize_filename(upload.filename)
    validate_pdf(filename, upload.file)

    user_dir = settings.upload_dir / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid4().hex}.pdf"
    final_path = user_dir / stored_filename
    temp_path = final_path.with_suffix(".part")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    sha256 = hashlib.sha256()
    size = 0

    try:
        # Stream to a temporary file, hashing and counting bytes as we go. The real size is
        # measured here because the size the client claims cannot be trusted.
        with temp_path.open("wb") as out:
            while chunk := upload.file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > max_bytes:
                    raise FileRejected(f"File is larger than {settings.MAX_UPLOAD_SIZE_MB} MB")
                sha256.update(chunk)
                out.write(chunk)

        check_active_content(temp_path)
        digest = sha256.hexdigest()
        if db.scalar(select(Document.id).where(Document.user_id == user_id, Document.sha256 == digest)):
            raise FileRejected("You have already uploaded this file")

        temp_path.replace(final_path)
    finally:
        temp_path.unlink(missing_ok=True)

    document = Document(
        user_id=user_id,
        original_filename=filename,
        stored_filename=stored_filename,
        content_type="application/pdf",
        file_size=size,
        sha256=digest,
    )
    db.add(document)
    try:
        db.commit()
    except IntegrityError:
        # The same file was uploaded twice at the same moment; the unique constraint caught it.
        db.rollback()
        final_path.unlink(missing_ok=True)
        raise FileRejected("You have already uploaded this file") from None

    db.refresh(document)
    logger.info("User %s uploaded document %s (%s bytes)", user_id, document.id, size)
    return document


def list_documents(db: Session, user_id: int) -> list[Document]:
    return list(db.scalars(select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc())))


def get_user_document(db: Session, user_id: int, document_id: int) -> Document | None:
    """Fetch a document only if it belongs to this user.

    Filtering by user_id in the query itself (not checking afterwards) is what keeps
    one user from ever reading another user's documents.
    """
    return db.scalar(select(Document).where(Document.id == document_id, Document.user_id == user_id))


def delete_document(db: Session, document: Document) -> None:
    path = document_path(document)
    document_id = document.id
    extracted = settings.extracted_dir / str(document_id)
    db.delete(document)
    db.commit()
    # Delete files after the database commit: an orphaned file is harmless,
    # but a database row pointing at a missing file would break the app.
    path.unlink(missing_ok=True)
    shutil.rmtree(extracted, ignore_errors=True)
    try:
        get_vector_store().delete_document(document_id)
    except Exception:  # a stale vector is harmless: search skips chunks that no longer exist
        logger.exception("Could not delete vectors of document %s", document_id)
