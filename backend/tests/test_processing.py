import cv2
import numpy as np
import pymupdf
import pytest

from app.core.config import settings
from app.services.processing import ocr
from app.services.processing.extractor import extract_document, guess_title
from app.services.processing.tables import rows_to_markdown
from tests import pdf_factory

DOCS_URL = "/api/v1/documents"


# ---------- Unit tests: extraction without the database ----------


def run_extraction(pdf_bytes: bytes, tmp_path):
    path = tmp_path / "input.pdf"
    path.write_bytes(pdf_bytes)
    with pymupdf.open(path) as pdf:
        return extract_document(pdf, path, tmp_path / "out")


def test_two_column_page_is_read_column_by_column(tmp_path):
    text = run_extraction(pdf_factory.two_column_pdf(), tmp_path).pages[0].text

    positions = [text.index(marker) for marker in ("A Study", "LEFT-FIRST", "LEFT-SECOND", "RIGHT-FIRST")]
    assert positions == sorted(positions)


def test_repeated_headers_and_footers_are_removed(tmp_path):
    pages = run_extraction(pdf_factory.header_footer_pdf(), tmp_path).pages

    for number, page in enumerate(pages, start=1):
        assert f"Body text number {number}" in page.text
        assert "Journal of Testing" not in page.text
        assert "Page" not in page.text


def test_table_is_extracted_as_markdown(tmp_path):
    result = run_extraction(pdf_factory.table_pdf(), tmp_path)

    [table] = [e for e in result.elements if e.element_type == "table"]
    assert table.content.splitlines()[0] == "| Model | Accuracy | F1 |"
    assert "| BERT | 91.2 | 90.1 |" in table.content
    assert table.extra == {"rows": 3, "cols": 3}


def test_rows_to_markdown_cleans_cells():
    markdown, rows, cols = rows_to_markdown([["A", None, ""], ["x|y", "multi\nline", ""], [None, None, None]])

    assert (rows, cols) == (2, 2)
    assert markdown == "| A | Column 2 |\n| --- | --- |\n| x\\|y | multi line |"


def test_raster_image_is_saved_as_png(tmp_path):
    result = run_extraction(pdf_factory.image_pdf(), tmp_path)

    [image] = [e for e in result.elements if e.element_type == "image"]
    assert image.page_number == 1
    assert image.image_path.read_bytes().startswith(b"\x89PNG")
    assert image.extra == {"width": 400, "height": 300}


def test_vector_chart_is_rendered_as_figure(tmp_path):
    result = run_extraction(pdf_factory.vector_chart_pdf(), tmp_path)

    figures = [e for e in result.elements if e.element_type == "figure"]
    assert len(figures) == 1
    assert figures[0].image_path.is_file()


def test_scanned_page_without_tesseract_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(ocr, "tesseract_available", lambda: False)

    result = run_extraction(pdf_factory.scanned_pdf(), tmp_path)

    assert result.pages[0].method == "ocr_unavailable"
    assert "Tesseract OCR is not installed" in result.notes[0]


@pytest.mark.skipif(not ocr.tesseract_available(), reason="Tesseract OCR is not installed")
def test_scanned_page_is_read_with_ocr(tmp_path):
    page = run_extraction(pdf_factory.scanned_pdf(), tmp_path).pages[0]

    assert page.method == "ocr"
    assert "PHOTOSYNTHESIS" in page.text.upper()


def test_skew_estimate_undoes_rotation():
    image = np.full((600, 800), 255, dtype=np.uint8)
    for y in range(80, 560, 40):  # fake text lines
        cv2.rectangle(image, (60, y), (740, y + 12), 0, thickness=-1)

    tilted = ocr.rotate(image, 3.0)

    assert ocr.estimate_skew(tilted) == pytest.approx(-3.0, abs=0.5)


def test_title_comes_from_metadata_or_largest_text(tmp_path):
    with pymupdf.open(stream=pdf_factory.text_pdf(["Body"], title="Attention Is All You Need")) as pdf:
        assert guess_title(pdf) == "Attention Is All You Need"
    with pymupdf.open(stream=pdf_factory.two_column_pdf()) as pdf:
        assert guess_title(pdf) == "A Study of Column Layouts"


# ---------- API tests: upload -> background processing -> results ----------


def upload(client, headers, content: bytes, name: str = "paper.pdf") -> int:
    body = client.post(DOCS_URL, headers=headers, files=[("files", (name, content, "application/pdf"))]).json()
    return body["uploaded"][0]["id"]


def test_upload_is_processed_in_the_background(client, make_user):
    headers = make_user()
    pdf = pdf_factory.text_pdf(["First page about transformers.", "Second page about attention."], title="My Paper")

    document_id = upload(client, headers, pdf)

    document = client.get(f"{DOCS_URL}/{document_id}", headers=headers).json()
    assert document["status"] == "ready"
    assert document["progress"] == 100
    assert document["page_count"] == 2
    assert document["title"] == "My Paper"
    assert document["is_scanned"] is False

    pages = client.get(f"{DOCS_URL}/{document_id}/pages", headers=headers).json()
    assert [(p["page_number"], p["extraction_method"]) for p in pages] == [(1, "native"), (2, "native")]
    page = client.get(f"{DOCS_URL}/{document_id}/pages/2", headers=headers).json()
    assert "Second page about attention." in page["text"]

    image = client.get(f"{DOCS_URL}/{document_id}/pages/1/image", headers=headers)
    assert image.headers["content-type"] == "image/png"
    assert image.content.startswith(b"\x89PNG")


def test_elements_api_returns_tables_and_images(client, make_user):
    headers = make_user()
    table_doc = upload(client, headers, pdf_factory.table_pdf(), "table.pdf")
    image_doc = upload(client, headers, pdf_factory.image_pdf(), "image.pdf")

    [table] = client.get(f"{DOCS_URL}/{table_doc}/elements", headers=headers).json()
    assert table["element_type"] == "table" and table["has_image"] is False
    assert "image_path" not in table  # internal paths are not exposed

    [image] = client.get(f"{DOCS_URL}/{image_doc}/elements?element_type=image", headers=headers).json()
    response = client.get(f"{DOCS_URL}/{image_doc}/elements/{image['id']}/image", headers=headers)
    assert response.status_code == 200
    assert response.content.startswith(b"\x89PNG")


def test_encrypted_pdf_fails_with_helpful_message(client, make_user):
    headers = make_user()

    document_id = upload(client, headers, pdf_factory.encrypted_pdf())

    document = client.get(f"{DOCS_URL}/{document_id}", headers=headers).json()
    assert document["status"] == "failed"
    assert "Password-protected" in document["error_message"]


def test_corrupted_pdf_fails(client, make_user):
    headers = make_user()

    document_id = upload(client, headers, b"%PDF-1.4\nthis is not really a pdf")

    assert client.get(f"{DOCS_URL}/{document_id}", headers=headers).json()["status"] == "failed"


def test_reprocess_replaces_previous_results(client, make_user):
    headers = make_user()
    document_id = upload(client, headers, pdf_factory.table_pdf())

    response = client.post(f"{DOCS_URL}/{document_id}/reprocess", headers=headers)

    assert response.status_code == 202
    assert client.get(f"{DOCS_URL}/{document_id}", headers=headers).json()["status"] == "ready"
    assert len(client.get(f"{DOCS_URL}/{document_id}/pages", headers=headers).json()) == 1
    assert len(client.get(f"{DOCS_URL}/{document_id}/elements", headers=headers).json()) == 1


def test_delete_removes_extracted_files(client, make_user):
    headers = make_user()
    document_id = upload(client, headers, pdf_factory.image_pdf())
    extracted = settings.extracted_dir / str(document_id)
    assert any(extracted.iterdir())

    client.delete(f"{DOCS_URL}/{document_id}", headers=headers)

    assert not extracted.exists()


def test_other_users_cannot_read_pages_or_elements(client, make_user):
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")
    document_id = upload(client, alice, pdf_factory.image_pdf())
    [element] = client.get(f"{DOCS_URL}/{document_id}/elements", headers=alice).json()

    for path in ("/pages", "/pages/1", "/pages/1/image", "/elements", f"/elements/{element['id']}/image"):
        assert client.get(f"{DOCS_URL}/{document_id}{path}", headers=bob).status_code == 404
    assert client.post(f"{DOCS_URL}/{document_id}/reprocess", headers=bob).status_code == 404
