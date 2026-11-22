"""Multimodal understanding of figures, charts, diagrams and images (Module 7).

Ingestion: each extracted picture is described by Gemini's vision model. The
description is stored as the element's content and chunked like text, so a question
such as "what does the loss curve show?" can retrieve the chart.
Answering: when a retrieved passage is a figure, the image itself is attached to the
LLM prompt, so the model can read values from it directly.
Fallback without an API key: OCR the image's text (if Tesseract is installed).
"""

import logging
import re
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, object_session

from app.core.config import settings
from app.models import Document, DocumentElement, DocumentPage
from app.services.llm import client as llm_client
from app.services.llm.client import ImageInput, LLMError, LLMNotConfigured
from app.services.processing import ocr

if TYPE_CHECKING:
    from app.services.rag.pipeline import SourcePassage

logger = logging.getLogger(__name__)

PICTURE_TYPES = ("figure", "image")
CAPTION = re.compile(r"((?:Figure|Fig\.|Chart|Diagram|Table)\s*\d+[.:]?[^\n]{0,300})", re.IGNORECASE)

FIGURE_SYSTEM = """You describe figures extracted from documents (charts, plots, diagrams, tables, photos)
so they can be found by a search engine and used to answer questions.
Describe only what is visible. Include: the type of visual; title or caption if visible; axes,
units and legend; the most important values, comparisons and trends; and any readable text.
Never invent values that cannot be read. Be concise (at most 120 words)."""


class FigureDescription(BaseModel):
    kind: str = Field(description="e.g. bar chart, line plot, flow diagram, table, photo")
    description: str
    visible_text: str = Field(default="", description="Important text or numbers readable in the image")


def _page_captions(db: Session, document_id: int, page_number: int) -> str:
    text = db.scalar(
        select(DocumentPage.text).where(DocumentPage.document_id == document_id, DocumentPage.page_number == page_number)
    )
    return " | ".join(CAPTION.findall(text or ""))[:800]


def _ocr_fallback(element: DocumentElement, path) -> bool:
    if not ocr.tesseract_available():
        return False
    import cv2

    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    text = ocr.ocr_image(image) if image is not None else ""
    if len(text) < 20:
        return False
    element.content = f"Image containing the text: {text[:1500]}"
    element.extra = {**(element.extra or {}), "description_source": "ocr"}
    return True


def describe_figures(db: Session, document: Document, on_progress: Callable[[int, int], None] | None = None) -> list[str]:
    """Fill in `content` for the document's pictures. Returns notes for the user."""
    if not settings.DESCRIBE_FIGURES:
        return []
    elements = [
        e
        for e in db.scalars(
            select(DocumentElement).where(
                DocumentElement.document_id == document.id,
                DocumentElement.element_type.in_(PICTURE_TYPES),
                DocumentElement.image_path.is_not(None),
            )
        )
        if not e.content
    ]
    if not elements:
        return []
    # Describe the biggest pictures first: they are most likely real figures, not decoration.
    elements.sort(key=lambda e: (e.extra or {}).get("width", 0) * (e.extra or {}).get("height", 0), reverse=True)

    try:
        llm = llm_client.get_llm()
    except LLMNotConfigured:
        described = sum(_ocr_fallback(e, settings.extracted_dir / e.image_path) for e in elements)
        db.commit()
        return [f"{len(elements) - described} figure(s) were not described because no Gemini API key is configured."]

    to_describe = elements[: settings.MAX_FIGURES_TO_DESCRIBE]
    failed = 0
    for index, element in enumerate(to_describe):
        if index:
            time.sleep(settings.FIGURE_DESCRIPTION_DELAY_S)  # stay under the free-tier rate limit
        path = settings.extracted_dir / element.image_path
        captions = _page_captions(db, document.id, element.page_number)
        prompt = f"This {element.element_type} is from page {element.page_number} of '{document.title or document.original_filename}'."
        if captions:
            prompt += f"\nCaptions found on that page (may or may not belong to this figure): {captions}"
        try:
            result = llm.generate_json(FIGURE_SYSTEM, prompt, FigureDescription, images=[ImageInput(data=path.read_bytes())])
        except (LLMError, OSError) as exc:
            logger.warning("Could not describe element %s: %s", element.id, exc)
            failed += 1
            if "rate limit" in str(exc):
                failed += len(to_describe) - index - 1
                break
            continue
        element.content = f"{result.kind.strip().capitalize()}: {result.description.strip()}"
        if result.visible_text.strip():
            element.content += f" Text in the figure: {result.visible_text.strip()}"
        element.extra = {**(element.extra or {}), "description_source": "gemini"}
        db.commit()
        if on_progress:
            on_progress(index + 1, len(to_describe))

    notes = []
    if failed:
        notes.append(f"{failed} figure(s) could not be described by the vision model.")
    if len(elements) > len(to_describe):
        notes.append(f"Only the {len(to_describe)} largest figures were described.")
    return notes


def load_figure_images(sources: list["SourcePassage"]) -> list[ImageInput]:
    """Images for retrieved figure passages, attached to the answer prompt."""
    images = []
    for source in sources:
        chunk = source.chunk
        if chunk.element_type not in PICTURE_TYPES or not chunk.element_id:
            continue
        element = object_session(chunk).get(DocumentElement, chunk.element_id)
        if element is None or not element.image_path:
            continue
        path = settings.extracted_dir / element.image_path
        if path.is_file():
            images.append(ImageInput(data=path.read_bytes()))
        if len(images) >= settings.MAX_IMAGES_PER_ANSWER:
            break
    return images
