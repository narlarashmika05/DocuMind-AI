from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import LongText

if TYPE_CHECKING:
    from app.models.document import Document


class DocumentPage(Base):
    """Clean text of one PDF page, in reading order."""

    __tablename__ = "document_pages"
    __table_args__ = (UniqueConstraint("document_id", "page_number", name="uq_document_pages_doc_page"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    page_number: Mapped[int]  # 1-based, as humans count pages
    text: Mapped[str] = mapped_column(LongText)
    # native = PDF text layer, ocr = Tesseract, empty = blank page,
    # ocr_unavailable = scanned page but Tesseract is not installed
    extraction_method: Mapped[str] = mapped_column(String(20))
    char_count: Mapped[int]
    width: Mapped[float]
    height: Mapped[float]

    document: Mapped["Document"] = relationship(back_populates="pages")
