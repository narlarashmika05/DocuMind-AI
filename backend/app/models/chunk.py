from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import LongText

if TYPE_CHECKING:
    from app.models.document import Document


class Chunk(Base):
    """A passage of a document. MySQL is the source of truth; ChromaDB only stores its vector.

    Keeping the text here means the vector index can be rebuilt at any time, keyword
    search (BM25) can run over the same chunks, and citations can show the exact passage.
    """

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    page_number: Mapped[int]
    chunk_index: Mapped[int]  # position within the document
    element_type: Mapped[str] = mapped_column(String(20), default="text")
    element_id: Mapped[int | None] = mapped_column(ForeignKey("document_elements.id", ondelete="SET NULL"))
    text: Mapped[str] = mapped_column(LongText)
    token_count: Mapped[int]

    document: Mapped["Document"] = relationship(back_populates="chunks")
