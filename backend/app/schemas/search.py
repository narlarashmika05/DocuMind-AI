from typing import Literal

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=30)
    document_ids: list[int] | None = None
    mode: Literal["dense", "keyword", "hybrid"] = "hybrid"
    rerank: bool = True


class SearchHit(BaseModel):
    chunk_id: int
    document_id: int
    document_title: str
    page_number: int
    element_type: str
    text: str
    score: float


class SearchResponse(BaseModel):
    query: str
    mode: str
    hits: list[SearchHit]
    latency_ms: float
