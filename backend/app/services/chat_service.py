"""Conversations: ask a question, run the RAG pipeline, store the answer with citations and claims."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.clock import utcnow
from app.models import Citation, Claim, Conversation, Document, Message
from app.services.multilingual.language import detect_language
from app.services.rag.pipeline import RagAnswer, answer_question

DEFAULT_TITLE = "New conversation"


def get_user_conversation(db: Session, user_id: int, conversation_id: int) -> Conversation | None:
    return db.scalar(
        select(Conversation)
        .options(selectinload(Conversation.messages).selectinload(Message.citations))
        .options(selectinload(Conversation.messages).selectinload(Message.claims))
        .where(Conversation.id == conversation_id, Conversation.user_id == user_id)
    )


def owned_document_ids(db: Session, user_id: int, document_ids: list[int] | None) -> list[int] | None:
    """Keep only ids of documents the user owns (None = all documents)."""
    if not document_ids:
        return None
    return list(db.scalars(select(Document.id).where(Document.id.in_(document_ids), Document.user_id == user_id)))


def recent_history(conversation: Conversation, turns: int) -> list[tuple[str, str]]:
    """(question, English answer) pairs, oldest first."""
    pairs = []
    messages = conversation.messages
    for question, answer in zip(messages, messages[1:]):
        if question.role == "user" and answer.role == "assistant":
            pairs.append((question.content, answer.content_en or answer.content))
    return pairs[-turns:] if turns else []


def ask(
    db: Session,
    user_id: int,
    conversation: Conversation,
    question: str,
    answer_language: str,
    document_ids: list[int] | None,
    history_turns: int,
) -> tuple[Message, Message]:
    started = utcnow()
    result = answer_question(
        db,
        user_id,
        question,
        history=recent_history(conversation, history_turns),
        answer_language=answer_language,
        document_ids=document_ids if document_ids is not None else conversation.document_ids,
    )

    user_message = Message(role="user", content=question, language=detect_language(question))
    assistant_message = _assistant_message(result)
    assistant_message.latency_ms = round((utcnow() - started).total_seconds() * 1000, 1)
    conversation.messages.extend([user_message, assistant_message])
    if conversation.title == DEFAULT_TITLE:
        conversation.title = question[:80] + ("…" if len(question) > 80 else "")
    conversation.updated_at = utcnow()
    db.commit()
    db.refresh(assistant_message)
    return user_message, assistant_message


def _assistant_message(result: RagAnswer) -> Message:
    message = Message(
        role="assistant",
        content=result.display_text,
        content_en=result.english_text,
        language=result.answer_language,
        status=result.status,
        faithfulness_score=result.faithfulness,
        details={
            "english_question": result.english_question,
            "question_language": result.question_language,
            "timings_ms": result.timings,
            "warnings": result.warnings,
        },
    )
    message.citations = [
        Citation(
            number=source.number,
            chunk_id=source.chunk.id,
            document_id=source.chunk.document_id,
            document_title=source.chunk.document.title or source.chunk.document.original_filename,
            page_number=source.chunk.page_number,
            element_type=source.chunk.element_type,
            element_id=source.chunk.element_id,
            snippet=source.chunk.text[:2000],
            relevance_score=round(source.score, 4),
        )
        for source in result.sources
    ]
    message.claims = [
        Claim(
            position=index,
            text=claim.text,
            text_display=claim.text_display,
            cited_numbers=claim.citations,
            verdict=claim.check.verdict if claim.check else "not_checked",
            confidence=claim.check.confidence if claim.check else None,
            evidence_number=claim.check.evidence_number if claim.check else None,
            evidence_snippet=claim.check.evidence_snippet if claim.check else None,
        )
        for index, claim in enumerate(result.claims)
    ]
    return message
