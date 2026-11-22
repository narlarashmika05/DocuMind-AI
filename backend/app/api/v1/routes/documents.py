from typing import Annotated

import pymupdf
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.v1.deps import CurrentUser, DbSession, limit_by_user
from app.core.config import settings
from app.core.rate_limit import upload_limiter
from app.db.session import get_session_factory
from app.models import Document, DocumentElement, DocumentPage, DocumentStatus
from app.schemas.document import DocumentOut, ElementOut, PageOut, PageSummary, RejectedFile, UploadResult
from app.services import document_service
from app.services.processing.pipeline import process_document
from app.services.security.file_validator import FileRejected, sanitize_filename

router = APIRouter(prefix="/documents", tags=["documents"])

SessionFactory = Annotated[sessionmaker[Session], Depends(get_session_factory)]


def _get_owned_document(db: Session, user_id: int, document_id: int) -> Document:
    document = document_service.get_user_document(db, user_id, document_id)
    if document is None:
        # 404 (not 403) for other users' documents, so their existence is not revealed
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return document


@router.post("", response_model=UploadResult, dependencies=[limit_by_user(upload_limiter)])
def upload_documents(
    files: Annotated[list[UploadFile], File(description="One or more PDF files")],
    background_tasks: BackgroundTasks,
    session_factory: SessionFactory,
    current_user: CurrentUser,
    db: DbSession,
) -> UploadResult:
    """Upload PDFs. Each accepted file is processed in the background after this returns."""
    if len(files) > settings.MAX_FILES_PER_UPLOAD:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"You can upload at most {settings.MAX_FILES_PER_UPLOAD} files at once",
        )

    result = UploadResult(uploaded=[], rejected=[])
    for upload in files:
        try:
            document = document_service.save_upload(db, current_user.id, upload)
        except FileRejected as exc:
            result.rejected.append(RejectedFile(filename=sanitize_filename(upload.filename), reason=str(exc)))
            continue
        result.uploaded.append(DocumentOut.model_validate(document))
        background_tasks.add_task(process_document, document.id, session_factory)
    return result


@router.get("", response_model=list[DocumentOut])
def list_documents(current_user: CurrentUser, db: DbSession) -> list[Document]:
    return document_service.list_documents(db, current_user.id)


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, current_user: CurrentUser, db: DbSession) -> Document:
    return _get_owned_document(db, current_user.id, document_id)


@router.post("/{document_id}/reprocess", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED)
def reprocess_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    session_factory: SessionFactory,
    current_user: CurrentUser,
    db: DbSession,
) -> Document:
    document = _get_owned_document(db, current_user.id, document_id)
    if document.status == DocumentStatus.PROCESSING.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "This document is already being processed")
    document.status = DocumentStatus.UPLOADED.value
    document.progress = 0
    document.error_message = None
    db.commit()
    background_tasks.add_task(process_document, document.id, session_factory)
    return document


@router.get("/{document_id}/file")
def download_document(document_id: int, current_user: CurrentUser, db: DbSession) -> FileResponse:
    document = _get_owned_document(db, current_user.id, document_id)
    path = document_service.document_path(document)
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File is missing from storage")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=document.original_filename,
        content_disposition_type="inline",  # open in the browser's PDF viewer instead of downloading
    )


@router.get("/{document_id}/pages", response_model=list[PageSummary])
def list_pages(document_id: int, current_user: CurrentUser, db: DbSession) -> list[DocumentPage]:
    _get_owned_document(db, current_user.id, document_id)
    return list(
        db.scalars(
            select(DocumentPage).where(DocumentPage.document_id == document_id).order_by(DocumentPage.page_number)
        )
    )


@router.get("/{document_id}/pages/{page_number}", response_model=PageOut)
def get_page(document_id: int, page_number: int, current_user: CurrentUser, db: DbSession) -> DocumentPage:
    _get_owned_document(db, current_user.id, document_id)
    page = db.scalar(
        select(DocumentPage).where(DocumentPage.document_id == document_id, DocumentPage.page_number == page_number)
    )
    if page is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Page not found")
    return page


@router.get("/{document_id}/pages/{page_number}/image")
def render_page(
    document_id: int,
    page_number: int,
    current_user: CurrentUser,
    db: DbSession,
    zoom: Annotated[float, Query(ge=0.5, le=3.0)] = 1.5,
) -> Response:
    """Render one page as PNG, for the document viewer and citation previews."""
    document = _get_owned_document(db, current_user.id, document_id)
    path = document_service.document_path(document)
    with pymupdf.open(path) as pdf:
        if not 1 <= page_number <= pdf.page_count:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Page not found")
        png = pdf[page_number - 1].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).tobytes("png")
    return Response(png, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


@router.get("/{document_id}/elements", response_model=list[ElementOut])
def list_elements(
    document_id: int,
    current_user: CurrentUser,
    db: DbSession,
    element_type: str | None = None,
    page: int | None = None,
) -> list[ElementOut]:
    _get_owned_document(db, current_user.id, document_id)
    query = select(DocumentElement).where(DocumentElement.document_id == document_id)
    if element_type:
        query = query.where(DocumentElement.element_type == element_type)
    if page:
        query = query.where(DocumentElement.page_number == page)
    query = query.order_by(DocumentElement.page_number, DocumentElement.id)
    return [ElementOut.from_element(element) for element in db.scalars(query)]


@router.get("/{document_id}/elements/{element_id}/image")
def get_element_image(document_id: int, element_id: int, current_user: CurrentUser, db: DbSession) -> FileResponse:
    _get_owned_document(db, current_user.id, document_id)
    element = db.scalar(
        select(DocumentElement).where(DocumentElement.id == element_id, DocumentElement.document_id == document_id)
    )
    if element is None or element.image_path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image not found")
    path = (settings.extracted_dir / element.image_path).resolve()
    # Defence in depth: never serve a file outside the extracted folder.
    if not path.is_relative_to(settings.extracted_dir.resolve()) or not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image not found")
    return FileResponse(path, media_type="image/png")


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, current_user: CurrentUser, db: DbSession) -> None:
    document_service.delete_document(db, _get_owned_document(db, current_user.id, document_id))
