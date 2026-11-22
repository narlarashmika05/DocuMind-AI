from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.chunk import Chunk
    from app.models.document_element import DocumentElement
    from app.models.document_page import DocumentPage
    from app.models.user import User


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Document(TimestampMixin, Base):
    __tablename__ = "documents"
    # The same user cannot upload identical file contents twice.
    __table_args__ = (UniqueConstraint("user_id", "sha256", name="uq_documents_user_sha256"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    # Random name on disk; the user's filename is never used as a path.
    stored_filename: Mapped[str] = mapped_column(String(64), unique=True)
    content_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    page_count: Mapped[int | None]
    # Stored as a plain string (not a MySQL ENUM) so adding a status later needs no table rewrite.
    status: Mapped[str] = mapped_column(String(20), default=DocumentStatus.UPLOADED.value)
    error_message: Mapped[str | None] = mapped_column(Text)

    # ---------- Filled in by the processing pipeline (Module 3) ----------
    title: Mapped[str | None] = mapped_column(String(500))
    is_scanned: Mapped[bool] = mapped_column(default=False)
    processing_stage: Mapped[str | None] = mapped_column(String(40))
    progress: Mapped[int] = mapped_column(default=0)  # 0-100, shown in the UI
    # Non-fatal problems worth telling the user about (e.g. "OCR is not installed")
    processing_notes: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)
    processing_seconds: Mapped[float | None]

    # ---------- How the document was indexed (Module 4) ----------
    # If the configured model or strategy changes, the document must be reprocessed.
    embedding_model: Mapped[str | None] = mapped_column(String(60))
    chunk_strategy: Mapped[str | None] = mapped_column(String(20))
    chunk_count: Mapped[int] = mapped_column(default=0)

    owner: Mapped["User"] = relationship(back_populates="documents")
    pages: Mapped[list["DocumentPage"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )
    elements: Mapped[list["DocumentElement"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )
