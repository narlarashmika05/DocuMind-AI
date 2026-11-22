from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import UTCDateTime


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    document_ids: list[int] | None = None


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    document_ids: list[int] | None = None


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    document_ids: list[int] | None
    created_at: UTCDateTime
    updated_at: UTCDateTime


class CitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    number: int
    chunk_id: int | None
    document_id: int | None
    document_title: str
    page_number: int
    element_type: str
    element_id: int | None
    snippet: str
    relevance_score: float


class ClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    position: int
    text: str
    text_display: str
    cited_numbers: list[int]
    verdict: str
    confidence: float | None
    evidence_number: int | None
    evidence_snippet: str | None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    language: str
    status: str | None
    faithfulness_score: float | None
    latency_ms: float | None
    details: dict[str, Any] | None
    created_at: UTCDateTime
    citations: list[CitationOut] = []
    claims: list[ClaimOut] = []


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]


class AskRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    # auto = answer in the same language as the question
    answer_language: Literal["auto", "en", "te"] = "auto"
    document_ids: list[int] | None = None

    @field_validator("content")
    @classmethod
    def strip(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question must not be empty")
        return value.strip()


class AskResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
