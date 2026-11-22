"""Extract pictures from a PDF page.

Two kinds exist:
- Raster images embedded in the PDF (photos, screenshots, scanned charts).
- Vector figures drawn with lines and shapes (most charts in research papers). These
  are not "images" inside the PDF, so we find clusters of drawings and render that area.
"""

import logging
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from app.core.config import settings

logger = logging.getLogger(__name__)

MIN_DISPLAY_SIZE_PT = 50  # smaller on the page than this = icon/bullet
MIN_FIGURE_AREA_FRACTION = 0.04


@dataclass
class ExtractedImage:
    kind: str  # "image" or "figure"
    path: Path
    width: int
    height: int
    bbox: list[float]


def count_image_usage(pdf: pymupdf.Document) -> Counter[int]:
    """How many pages each embedded image appears on. Logos repeat on every page."""
    usage: Counter[int] = Counter()
    for page in pdf:
        usage.update({image[0] for image in page.get_images(full=True)})
    return usage


def _round_rect(rect: pymupdf.Rect) -> list[float]:
    return [round(v, 1) for v in (rect.x0, rect.y0, rect.x1, rect.y1)]


def extract_raster_images(
    pdf: pymupdf.Document, page: pymupdf.Page, out_dir: Path, usage: Counter[int]
) -> list[ExtractedImage]:
    results = []
    for index, image in enumerate(page.get_images(full=True), start=1):
        xref = image[0]
        if usage[xref] >= 3:  # repeated logo or watermark
            continue
        rects = page.get_image_rects(xref)
        if not rects or rects[0].width < MIN_DISPLAY_SIZE_PT or rects[0].height < MIN_DISPLAY_SIZE_PT:
            continue
        try:
            pixmap = pymupdf.Pixmap(pdf, xref)
            if pixmap.width < settings.MIN_IMAGE_SIZE_PX or pixmap.height < settings.MIN_IMAGE_SIZE_PX:
                continue
            if pixmap.n - pixmap.alpha >= 4:  # CMYK -> RGB so browsers can show it
                pixmap = pymupdf.Pixmap(pymupdf.csRGB, pixmap)
            path = out_dir / f"p{page.number + 1}_img{index}.png"
            pixmap.save(path)
        except (RuntimeError, ValueError) as exc:  # unusual image encodings
            logger.warning("Skipping image xref %s on page %s: %s", xref, page.number + 1, exc)
            continue
        results.append(ExtractedImage("image", path, pixmap.width, pixmap.height, _round_rect(rects[0])))
    return results


def _overlaps(rect: pymupdf.Rect, others: list[pymupdf.Rect], threshold: float = 0.5) -> bool:
    area = rect.width * rect.height
    for other in others:
        inter = rect & other
        if not inter.is_empty and area and (inter.width * inter.height) / area > threshold:
            return True
    return False


def extract_vector_figures(page: pymupdf.Page, out_dir: Path, skip_areas: list[list[float]]) -> list[ExtractedImage]:
    """Render areas with many vector drawings (charts, diagrams) as PNG images."""
    page_area = page.rect.width * page.rect.height
    skip_rects = [pymupdf.Rect(*bbox) for bbox in skip_areas]
    results = []
    try:
        clusters = page.cluster_drawings()
    except (AttributeError, RuntimeError, ValueError):  # very old PyMuPDF or malformed drawings
        return results

    for index, rect in enumerate(clusters, start=1):
        area = rect.width * rect.height
        if area < page_area * MIN_FIGURE_AREA_FRACTION or area > page_area * 0.9:
            continue  # too small to be a figure, or just a page border
        if rect.width < 100 or rect.height < 60 or _overlaps(rect, skip_rects):
            continue  # tables are drawn with lines too; they are handled separately
        clip = (rect + (-8, -8, 8, 8)) & page.rect  # small margin around the drawing
        pixmap = page.get_pixmap(clip=clip, dpi=150)
        path = out_dir / f"p{page.number + 1}_fig{index}.png"
        pixmap.save(path)
        results.append(ExtractedImage("figure", path, pixmap.width, pixmap.height, _round_rect(clip)))
    return results
