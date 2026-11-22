from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utcnow
from app.db.base import Base, TimestampMixin
from app.db.types import LongText


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="New conversation")
    # Restrict answers to these documents; null = all of the user's documents
    document_ids: Mapped[list[int] | None] = mapped_column(JSON)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Message.id",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # user | assistant
    content: Mapped[str] = mapped_column(LongText)  # shown to the user, in their language
    content_en: Mapped[str | None] = mapped_column(LongText)  # English version (used for history + verification)
    language: Mapped[str] = mapped_column(String(5), default="en")
    # answered | insufficient_information (assistant messages only)
    status: Mapped[str | None] = mapped_column(String(30))
    faithfulness_score: Mapped[float | None] = mapped_column(Float)  # Module 8
    latency_ms: Mapped[float | None] = mapped_column(Float)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # timings, rewritten question, warnings
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    citations: Mapped[list["Citation"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="Citation.number"
    )
    claims: Mapped[list["Claim"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="Claim.position"
    )


class Citation(Base):
    """A source passage given to the LLM for an answer, numbered as in the prompt ([1], [2], ...).

    The snippet and document title are copied, so old answers still show their sources
    after the document is deleted (chunk_id then becomes NULL).
    """

    __tablename__ = "citations"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), index=True)
    number: Mapped[int]
    chunk_id: Mapped[int | None] = mapped_column(ForeignKey("chunks.id", ondelete="SET NULL"))
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    document_title: Mapped[str] = mapped_column(String(500))
    page_number: Mapped[int]
    element_type: Mapped[str] = mapped_column(String(20), default="text")
    element_id: Mapped[int | None]
    snippet: Mapped[str] = mapped_column(Text)
    relevance_score: Mapped[float] = mapped_column(Float)


class Claim(Base):
    """One sentence of an answer, with the result of checking it against its sources (Module 8)."""

    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), index=True)
    position: Mapped[int]
    text: Mapped[str] = mapped_column(Text)  # English
    text_display: Mapped[str] = mapped_column(Text)  # in the answer language
    cited_numbers: Mapped[list[int]] = mapped_column(JSON)
    # supported | partially_supported | unsupported | contradicted | not_checked
    verdict: Mapped[str] = mapped_column(String(30), default="not_checked")
    confidence: Mapped[float | None] = mapped_column(Float)
    evidence_number: Mapped[int | None]  # citation number of the best supporting passage
    evidence_snippet: Mapped[str | None] = mapped_column(Text)
