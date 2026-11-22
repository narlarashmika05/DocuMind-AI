from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.v1.deps import CurrentUser, DbSession, limit_by_user
from app.core.config import settings
from app.core.rate_limit import ask_limiter
from app.models import Conversation
from app.schemas.chat import (
    AskRequest,
    AskResponse,
    ConversationCreate,
    ConversationDetail,
    ConversationOut,
    ConversationUpdate,
    MessageOut,
)
from app.services import chat_service
from app.services.llm.client import LLMError, LLMNotConfigured

router = APIRouter(prefix="/conversations", tags=["chat"])


def _get_owned(db: DbSession, user_id: int, conversation_id: int) -> Conversation:
    conversation = chat_service.get_user_conversation(db, user_id, conversation_id)
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conversation


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(payload: ConversationCreate, current_user: CurrentUser, db: DbSession) -> Conversation:
    conversation = Conversation(
        user_id=current_user.id,
        title=payload.title or chat_service.DEFAULT_TITLE,
        document_ids=chat_service.owned_document_ids(db, current_user.id, payload.document_ids),
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("", response_model=list[ConversationOut])
def list_conversations(current_user: CurrentUser, db: DbSession) -> list[Conversation]:
    return list(
        db.scalars(
            select(Conversation)
            .where(Conversation.user_id == current_user.id)
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        )
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: int, current_user: CurrentUser, db: DbSession) -> Conversation:
    return _get_owned(db, current_user.id, conversation_id)


@router.patch("/{conversation_id}", response_model=ConversationOut)
def update_conversation(
    conversation_id: int, payload: ConversationUpdate, current_user: CurrentUser, db: DbSession
) -> Conversation:
    conversation = _get_owned(db, current_user.id, conversation_id)
    if payload.title is not None:
        conversation.title = payload.title
    if "document_ids" in payload.model_fields_set:
        conversation.document_ids = chat_service.owned_document_ids(db, current_user.id, payload.document_ids)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: int, current_user: CurrentUser, db: DbSession) -> None:
    db.delete(_get_owned(db, current_user.id, conversation_id))
    db.commit()


@router.post("/{conversation_id}/messages", response_model=AskResponse, dependencies=[limit_by_user(ask_limiter)])
def ask_question(conversation_id: int, payload: AskRequest, current_user: CurrentUser, db: DbSession) -> AskResponse:
    """Ask a question. Returns the stored question and the verified, cited answer."""
    conversation = _get_owned(db, current_user.id, conversation_id)
    document_ids = (
        chat_service.owned_document_ids(db, current_user.id, payload.document_ids)
        if payload.document_ids is not None
        else None
    )
    if payload.document_ids and not document_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "None of the selected documents were found")
    try:
        user_message, assistant_message = chat_service.ask(
            db,
            current_user.id,
            conversation,
            payload.content,
            payload.answer_language,
            document_ids,
            settings.HISTORY_TURNS,
        )
    except LLMNotConfigured as exc:
        db.rollback()
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from None
    except LLMError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from None
    return AskResponse(
        user_message=MessageOut.model_validate(user_message),
        assistant_message=MessageOut.model_validate(assistant_message),
    )
