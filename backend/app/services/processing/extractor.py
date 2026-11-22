"""Extract everything from one PDF: page text (native or OCR), tables and pictures.

This module knows nothing about the database, which keeps it easy to test and reuse
(the evaluation framework in Module 9 calls it directly).
"""

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pdfplumber
import pymupdf

from app.core.config import settings
from app.services.processing import images, ocr, tables, text_layout

logger = logging.getLogger(__name__)


@dataclass
class PageResult:
    page_number: int
    text: str
    method: str  # native | ocr | empty | ocr_unavailable
    width: float
    height: float


@dataclass
class ElementResult:
    page_number: int
    element_type: str  # table | image | figure
    content: str
    image_path: Path | None = None
    bbox: list[float] | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    pages: list[PageResult]
    elements: list[ElementResult]
    notes: list[str]

    @property
    def ocr_page_count(self) -> int:
        return sum(p.method == "ocr" for p in self.pages)


def guess_title(pdf: pymupdf.Document) -> str | None:
    """Use the PDF's title metadata if it is meaningful, otherwise the largest text on page 1."""
    meta_title = ((pdf.metadata or {}).get("title") or "").strip()
    if 4 <= len(meta_title) <= 300 and not re.search(r"untitled|microsoft word|\.(docx?|pdf|tex)$", meta_title, re.I):
        return meta_title

    spans = [
        span
        for block in pdf[0].get_text("dict")["blocks"]
        for line in block.get("lines", [])
        for span in line["spans"]
        if span["text"].strip() and span["bbox"][1] < pdf[0].rect.height / 2
    ]
    if not spans:
        return None
    largest = max(span["size"] for span in spans)
    title = " ".join(span["text"].strip() for span in spans if span["size"] >= largest - 0.5)
    return title[:300] if len(title) >= 4 else None


def needs_ocr(text: str, coverage: float) -> bool:
    little_text = len(text) < settings.MIN_TEXT_CHARS_PER_PAGE
    return (little_text and coverage > 0.3) or text_layout.looks_garbled(text)


def extract_document(
    pdf: pymupdf.Document,
    pdf_path: Path,
    out_dir: Path,
    on_progress: Callable[[int, int], None] | None = None,
) -> ExtractionResult:
    out_dir.mkdir(parents=True, exist_ok=True)
    page_count = pdf.page_count

    # Pass 1: text blocks for every page, so repeated headers/footers can be detected.
    blocks_per_page = [text_layout.read_blocks(page) for page in pdf]
    text_layout.remove_repeated_margins(blocks_per_page, [page.rect.height for page in pdf])
    image_usage = images.count_image_usage(pdf)

    pages: list[PageResult] = []
    elements: list[ElementResult] = []
    unreadable_scans = 0
    image_budget = settings.MAX_IMAGES_PER_DOCUMENT
    images_skipped = 0

    # Pass 2: page by page, so huge documents never sit fully in memory.
    with pdfplumber.open(pdf_path) as plumber:
        for index, page in enumerate(pdf):
            number = index + 1
            text = "\n\n".join(text_layout.order_blocks(blocks_per_page[index], page.rect.width))
            method = "native"

            if needs_ocr(text, text_layout.image_coverage(page)):
                if ocr.tesseract_available():
                    text, method = ocr.ocr_page(page), "ocr"
                else:
                    method = "ocr_unavailable"
                    unreadable_scans += 1
            if method == "native" and not text:
                method = "empty"

            pages.append(PageResult(number, text, method, page.rect.width, page.rect.height))

            # A scanned page is one big picture; its tables and figures cannot be separated.
            if method == "native":
                plumber_page = plumber.pages[index]
                page_tables = tables.extract_tables(plumber_page)
                plumber_page.close()  # release pdfplumber's per-page cache
                for table in page_tables:
                    elements.append(
                        ElementResult(
                            number,
                            "table",
                            table.markdown,
                            bbox=table.bbox,
                            extra={"rows": table.n_rows, "cols": table.n_cols},
                        )
                    )

                found = images.extract_raster_images(pdf, page, out_dir, image_usage)
                found += images.extract_vector_figures(page, out_dir, [t.bbox for t in page_tables])
                for picture in found:
                    if image_budget <= 0:
                        picture.path.unlink(missing_ok=True)
                        images_skipped += 1
                        continue
                    image_budget -= 1
                    elements.append(
                        ElementResult(
                            number,
                            picture.kind,
                            "",
                            image_path=picture.path,
                            bbox=picture.bbox,
                            extra={"width": picture.width, "height": picture.height},
                        )
                    )

            if on_progress:
                on_progress(number, page_count)

    notes = []
    if unreadable_scans:
        notes.append(
            f"{unreadable_scans} page(s) appear to be scanned, but Tesseract OCR is not installed, "
            "so their text could not be read."
        )
    if images_skipped:
        notes.append(f"Only the first {settings.MAX_IMAGES_PER_DOCUMENT} images were kept; {images_skipped} skipped.")
    return ExtractionResult(pages, elements, notes)
