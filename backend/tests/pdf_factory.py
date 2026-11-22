"""Build small, realistic PDFs in code so tests need no binary fixture files."""

import cv2
import numpy as np
import pymupdf

TABLE_CELLS = [["Model", "Accuracy", "F1"], ["BERT", "91.2", "90.1"], ["LSTM", "85.4", "84.0"]]


def _bytes(doc: pymupdf.Document, **save_options) -> bytes:
    data = doc.tobytes(**save_options)
    doc.close()
    return data


def text_pdf(pages: list[str], title: str | None = None) -> bytes:
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        page.insert_textbox(pymupdf.Rect(72, 72, 540, 720), text, fontsize=11)
    if title:
        doc.set_metadata({"title": title})
    return _bytes(doc)


def two_column_pdf() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_textbox(pymupdf.Rect(50, 50, 562, 90), "A Study of Column Layouts", fontsize=18)
    page.insert_textbox(pymupdf.Rect(50, 150, 290, 300), "LEFT-FIRST paragraph of the left column.", fontsize=10)
    page.insert_textbox(pymupdf.Rect(50, 400, 290, 550), "LEFT-SECOND paragraph of the left column.", fontsize=10)
    page.insert_textbox(pymupdf.Rect(322, 150, 562, 300), "RIGHT-FIRST paragraph of the right column.", fontsize=10)
    return _bytes(doc)


def header_footer_pdf(page_count: int = 4) -> bytes:
    doc = pymupdf.open()
    for n in range(1, page_count + 1):
        page = doc.new_page()
        page.insert_textbox(pymupdf.Rect(72, 20, 540, 45), "Journal of Testing, Volume 7", fontsize=9)
        page.insert_textbox(pymupdf.Rect(72, 300, 540, 400), f"Body text number {n} about neural networks.", fontsize=11)
        bottom = page.rect.height
        page.insert_textbox(pymupdf.Rect(72, bottom - 45, 540, bottom - 20), f"Page {n}", fontsize=9)
    return _bytes(doc)


def table_pdf() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_textbox(pymupdf.Rect(72, 40, 540, 90), "Table 1 compares model accuracy.", fontsize=11)
    xs, ys = [72, 222, 372, 522], [100, 130, 160, 190]
    for x in xs:
        page.draw_line((x, ys[0]), (x, ys[-1]))
    for y in ys:
        page.draw_line((xs[0], y), (xs[-1], y))
    for r, row in enumerate(TABLE_CELLS):
        for c, cell in enumerate(row):
            page.insert_text((xs[c] + 6, ys[r] + 20), cell, fontsize=10)
    return _bytes(doc)


def png_bytes(width: int = 400, height: int = 300) -> bytes:
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    cv2.rectangle(image, (40, 40), (width - 40, height - 40), (200, 80, 30), thickness=-1)
    cv2.putText(image, "CHART", (120, height // 2), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 4)
    return cv2.imencode(".png", image)[1].tobytes()


def image_pdf() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_textbox(pymupdf.Rect(72, 40, 540, 90), "Figure 1 shows the results.", fontsize=11)
    page.insert_image(pymupdf.Rect(72, 100, 372, 325), stream=png_bytes())
    return _bytes(doc)


def vector_chart_pdf() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_textbox(pymupdf.Rect(72, 40, 540, 90), "Figure 2: training loss per epoch.", fontsize=11)
    page.draw_line((100, 400), (500, 400))  # x axis
    page.draw_line((100, 400), (100, 150))  # y axis
    for i, height in enumerate([200, 150, 110, 80, 60, 50]):
        x = 120 + i * 60
        page.draw_rect(pymupdf.Rect(x, 400 - height, x + 40, 400), color=(0, 0, 1), fill=(0.3, 0.5, 0.9))
    return _bytes(doc)


def scanned_pdf(text: str = "PHOTOSYNTHESIS CONVERTS LIGHT INTO CHEMICAL ENERGY") -> bytes:
    """A page that contains only a picture of text, like a scanner produces."""
    source = pymupdf.open()
    page = source.new_page()
    page.insert_textbox(pymupdf.Rect(60, 100, 560, 400), text, fontsize=22)
    pixmap = page.get_pixmap(dpi=200)
    source.close()

    doc = pymupdf.open()
    scanned_page = doc.new_page()
    scanned_page.insert_image(scanned_page.rect, pixmap=pixmap)
    return _bytes(doc)


def encrypted_pdf() -> bytes:
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Secret content")
    return _bytes(doc, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="secret", owner_pw="owner")
