"""Turn a PDF page's text blocks into clean text in human reading order.

PDFs store text as positioned fragments, not paragraphs. Research papers add two
problems: two-column layouts (reading strictly top-to-bottom mixes the columns) and
running headers/footers (journal name, page numbers) repeated on every page.
"""

import re
from collections import Counter
from dataclasses import dataclass

import pymupdf

# Header/footer zone: top and bottom 10% of the page
MARGIN_FRACTION = 0.10


@dataclass
class TextBlock:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str


def clean_text(text: str) -> str:
    text = text.replace("­", "").replace("\x00", "")  # soft hyphens, NUL bytes
    text = re.sub(r"\s*\n\s*", " ", text)  # lines inside one block form one paragraph
    return re.sub(r"[ \t]+", " ", text).strip()


def read_blocks(page: pymupdf.Page) -> list[TextBlock]:
    # TEXT_DEHYPHENATE joins words split across lines ("exam-\nple" -> "example").
    flags = pymupdf.TEXT_DEHYPHENATE | pymupdf.TEXT_MEDIABOX_CLIP
    blocks = []
    for x0, y0, x1, y1, text, _block_no, block_type in page.get_text("blocks", flags=flags):
        if block_type == 0 and (cleaned := clean_text(text)):  # 0 = text, 1 = image
            blocks.append(TextBlock(x0, y0, x1, y1, cleaned))
    return blocks


def image_coverage(page: pymupdf.Page) -> float:
    """Fraction of the page area covered by raster images (close to 1.0 for scanned pages)."""
    page_area = page.rect.width * page.rect.height
    covered = 0.0
    for info in page.get_image_info():
        rect = pymupdf.Rect(info["bbox"]) & page.rect
        if not rect.is_empty:
            covered += rect.width * rect.height
    return min(1.0, covered / page_area) if page_area else 0.0


def order_blocks(blocks: list[TextBlock], page_width: float) -> list[str]:
    """Reading order for single- and two-column pages.

    Blocks spanning both columns (title, abstract, wide figures) act as section breaks.
    Between breaks, the whole left column is read before the right column.
    """
    middle = page_width / 2
    gutter = page_width * 0.05
    ordered: list[str] = []
    left: list[TextBlock] = []
    right: list[TextBlock] = []

    def flush_columns() -> None:
        ordered.extend(b.text for b in sorted(left, key=lambda b: b.y0))
        ordered.extend(b.text for b in sorted(right, key=lambda b: b.y0))
        left.clear()
        right.clear()

    for block in sorted(blocks, key=lambda b: (b.y0, b.x0)):
        if block.x1 <= middle + gutter:
            left.append(block)
        elif block.x0 >= middle - gutter:
            right.append(block)
        else:
            flush_columns()
            ordered.append(block.text)
    flush_columns()
    return ordered


def _margin_key(text: str) -> str:
    # "Page 3 of 10" and "Page 4 of 10" should count as the same footer.
    return re.sub(r"\d+", "#", text.lower()).strip()


def remove_repeated_margins(pages: list[list[TextBlock]], page_heights: list[float]) -> None:
    """Remove headers/footers that repeat on many pages (modifies `pages` in place)."""
    if len(pages) < 3:
        return

    def in_margin(block: TextBlock, height: float) -> bool:
        return block.y1 <= height * MARGIN_FRACTION or block.y0 >= height * (1 - MARGIN_FRACTION)

    counts: Counter[str] = Counter()
    for blocks, height in zip(pages, page_heights):
        counts.update({_margin_key(b.text) for b in blocks if in_margin(b, height)})

    threshold = max(3, len(pages) // 2)
    repeated = {key for key, count in counts.items() if count >= threshold}
    for i, (blocks, height) in enumerate(zip(pages, page_heights)):
        pages[i] = [b for b in blocks if not (in_margin(b, height) and _margin_key(b.text) in repeated)]


def looks_garbled(text: str) -> bool:
    """Some PDFs have a broken text layer (wrong font encoding) full of replacement characters."""
    if not text:
        return False
    bad = sum(1 for ch in text if ch == "�" or (not ch.isprintable() and ch not in "\n\t"))
    return bad / len(text) > 0.2
