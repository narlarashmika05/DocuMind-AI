from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.common import UTCDateTime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    title: str | None
    file_size: int
    page_count: int | None
    status: str
    processing_stage: str | None
    progress: int
    is_scanned: bool
    error_message: str | None
    processing_notes: str | None
    processing_seconds: float | None
    embedding_model: str | None
    chunk_strategy: str | None
    chunk_count: int
    created_at: UTCDateTime


class RejectedFile(BaseModel):
    filename: str
    reason: str


class UploadResult(BaseModel):
    """A batch upload can partly succeed, so the response reports each file."""

    uploaded: list[DocumentOut]
    rejected: list[RejectedFile]


class PageSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page_number: int
    extraction_method: str
    char_count: int


class PageOut(PageSummary):
    text: str
    width: float
    height: float


class ElementOut(BaseModel):
    id: int
    page_number: int
    element_type: str
    content: str
    bbox: list[float] | None
    extra: dict[str, Any] | None
    has_image: bool  # the internal storage path itself is never exposed

    @classmethod
    def from_element(cls, element: Any) -> "ElementOut":
        return cls(
            id=element.id,
            page_number=element.page_number,
            element_type=element.element_type,
            content=element.content,
            bbox=element.bbox,
            extra=element.extra,
            has_image=element.image_path is not None,
        )
