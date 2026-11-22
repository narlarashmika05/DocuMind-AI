import time

from fastapi import APIRouter

from app.api.v1.deps import CurrentUser, DbSession, limit_by_user
from app.core.rate_limit import search_limiter
from app.schemas.search import SearchHit, SearchRequest, SearchResponse
from app.services.retrieval.retriever import retrieve

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse, dependencies=[limit_by_user(search_limiter)])
def search(payload: SearchRequest, current_user: CurrentUser, db: DbSession) -> SearchResponse:
    """Retrieval only, without the LLM. Useful for debugging and for the evaluation dashboard."""
    started = time.perf_counter()
    results = retrieve(
        db,
        current_user.id,
        payload.query,
        top_k=payload.top_k,
        mode=payload.mode,
        rerank=payload.rerank,
        document_ids=payload.document_ids,
    )
    return SearchResponse(
        query=payload.query,
        mode=payload.mode,
        latency_ms=round((time.perf_counter() - started) * 1000, 1),
        hits=[
            SearchHit(
                chunk_id=item.chunk.id,
                document_id=item.chunk.document_id,
                document_title=item.chunk.document.title or item.chunk.document.original_filename,
                page_number=item.chunk.page_number,
                element_type=item.chunk.element_type,
                text=item.chunk.text,
                score=round(item.score, 4),
            )
            for item in results
        ],
    )
