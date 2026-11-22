"""OCR for scanned pages: render the page as an image, clean it with OpenCV, read it with Tesseract.

Tesseract is a separate program (not a Python package). If it is not installed, the
pipeline still works; scanned pages are marked "ocr_unavailable" and the user is told.
"""

import logging
import re
import shutil
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
import pymupdf
import pytesseract

from app.core.config import settings

logger = logging.getLogger(__name__)

WINDOWS_DEFAULT_PATH = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


@lru_cache
def tesseract_available() -> bool:
    command = settings.TESSERACT_CMD or shutil.which("tesseract")
    if not command and WINDOWS_DEFAULT_PATH.exists():
        command = str(WINDOWS_DEFAULT_PATH)
    if not command:
        logger.warning("Tesseract OCR not found; scanned pages will not be readable")
        return False

    pytesseract.pytesseract.tesseract_cmd = command
    try:
        logger.info("Using Tesseract %s", pytesseract.get_tesseract_version())
        return True
    except (pytesseract.TesseractNotFoundError, OSError):
        logger.warning("Tesseract at %s could not be started", command)
        return False


@lru_cache
def ocr_languages() -> str:
    """Requested languages that are actually installed, e.g. "eng+tel"."""
    installed = set(pytesseract.get_languages(config=""))
    usable = [lang for lang in settings.OCR_LANGUAGES.split("+") if lang in installed]
    missing = set(settings.OCR_LANGUAGES.split("+")) - installed
    if missing:
        logger.warning("Tesseract language data missing for: %s", ", ".join(sorted(missing)))
    return "+".join(usable) or "eng"


def render_page_gray(page: pymupdf.Page, dpi: int) -> np.ndarray:
    pixmap = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
    return np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width)


def estimate_skew(binary: np.ndarray, max_angle: float = 5.0, step: float = 0.5) -> float:
    """Find the rotation (degrees) that makes text lines horizontal.

    When lines are horizontal, each row of pixels is either mostly ink or mostly blank,
    so the row sums vary the most. We try small angles and keep the one with the
    highest variance (a "projection profile").
    """
    height, width = binary.shape
    scale = 800 / width if width > 800 else 1.0
    small = cv2.resize(binary, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
    ink = (small < 128).astype(np.float32)
    h, w = ink.shape

    best_angle, best_score = 0.0, -1.0
    for angle in np.arange(-max_angle, max_angle + step / 2, step):
        matrix = cv2.getRotationMatrix2D((w / 2, h / 2), float(angle), 1.0)
        rotated = cv2.warpAffine(ink, matrix, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)
        score = float(np.var(rotated.sum(axis=1)))
        if score > best_score:
            best_angle, best_score = float(angle), score
    return best_angle


def rotate(image: np.ndarray, angle: float) -> np.ndarray:
    if angle == 0:
        return image
    h, w = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_LINEAR, borderValue=255)


def preprocess(gray: np.ndarray) -> np.ndarray:
    """Denoise -> black/white (Otsu threshold) -> straighten. Clean input = better OCR."""
    denoised = cv2.medianBlur(gray, 3)
    _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return rotate(binary, estimate_skew(binary))


def ocr_image(image: np.ndarray) -> str:
    text = pytesseract.image_to_string(image, lang=ocr_languages(), config="--psm 3")
    # Keep paragraph breaks (blank lines); join lines within a paragraph.
    paragraphs = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text)]
    return "\n\n".join(p for p in paragraphs if p)


def ocr_page(page: pymupdf.Page) -> str:
    return ocr_image(preprocess(render_page_gray(page, settings.OCR_DPI)))
