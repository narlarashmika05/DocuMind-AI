from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import LongText

if TYPE_CHECKING:
    from app.models.document import Document


class ElementType(StrEnum):
    TABLE = "table"  # content = Markdown table
    IMAGE = "image"  # embedded raster image (photo, scanned chart, screenshot)
    FIGURE = "figure"  # vector drawing (most charts and diagrams in research papers)


class DocumentElement(Base):
    """A non-text part of a page: a table, an image or a figure."""

    __tablename__ = "document_elements"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    page_number: Mapped[int]
    element_type: Mapped[str] = mapped_column(String(20))
    # Table: Markdown. Image/figure: description (Module 7) or OCR text; empty until described.
    content: Mapped[str] = mapped_column(LongText, default="")
    # Relative to settings.extracted_dir, e.g. "12/images/p3_1.png"
    image_path: Mapped[str | None] = mapped_column(String(500))
    bbox: Mapped[list[float] | None] = mapped_column(JSON)  # [x0, y0, x1, y1] in PDF points
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    document: Mapped["Document"] = relationship(back_populates="elements")
