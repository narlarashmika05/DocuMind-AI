# Module 3 – Intelligent Document Processing

## Objective
Turn every uploaded PDF into clean, structured content — page text in reading order, tables as Markdown, and pictures as PNG files — automatically, in the background, for normal *and* scanned PDFs.

## Concepts

| Concept | Explanation |
|---|---|
| **PDF text layer** | A PDF does not store paragraphs. It stores positioned fragments ("draw 'Hello' at x=72, y=100"). We must rebuild reading order ourselves. |
| **Reading order / two-column layout** | Research papers use two columns. Reading strictly top-to-bottom would mix them. We read the left column, then the right, using blocks that span both columns (title, abstract) as section breaks. |
| **Header/footer removal** | Text in the top/bottom 10% of the page that repeats on many pages (journal name, "Page 3") is noise for search and is removed. |
| **Scanned PDF detection** | A page with almost no text that is mostly covered by an image is a scan. A garbled text layer (wrong font encoding) is also sent to OCR. |
| **OCR (Optical Character Recognition)** | Tesseract reads text from an image. It uses an LSTM neural network trained on many fonts and languages. |
| **Image preprocessing (OpenCV)** | Median blur removes speckles, Otsu thresholding makes pure black/white, deskewing straightens tilted scans. Clean input = far better OCR. |
| **Projection-profile deskew** | When text lines are horizontal, row sums of ink alternate strongly between lines and gaps (high variance). We try angles −5°…+5° and keep the one with maximum variance. |
| **Raster vs vector graphics** | Photos are raster (pixels) and can be extracted directly. Most charts in papers are vector (lines/shapes) — we detect clusters of drawings and render that region as an image. |
| **Background jobs** | Processing takes seconds to minutes, so the upload returns immediately and a background task does the work, updating `status`, `processing_stage` and `progress` for the UI. |
| **Idempotency** | Reprocessing deletes all previous results first, so running a job twice never creates duplicates. |

## Workflow

```
Upload → documents.status = uploaded → BackgroundTask: process_document()
  open PDF  ── encrypted? empty? too many pages? → status = failed + helpful message
  pass 1: text blocks of every page → remove repeated headers/footers
  pass 2 (page by page):
     text = blocks in reading order
     needs OCR? → Tesseract (or mark "ocr_unavailable" if not installed)
     native page → pdfplumber tables → Markdown
                 → raster images (skip logos/icons) → PNG
                 → vector figures (drawing clusters, not tables) → PNG
  save document_pages + document_elements → status = ready, progress = 100
```

## New database tables

| Table | Key columns |
|---|---|
| `document_pages` | document_id, page_number, text (MEDIUMTEXT), extraction_method (native/ocr/empty/ocr_unavailable), char_count |
| `document_elements` | document_id, page_number, element_type (table/image/figure), content (Markdown or description), image_path, bbox (JSON) |
| `documents` (new columns) | title, is_scanned, processing_stage, progress, processing_notes, processed_at, processing_seconds |

## Files

| File | Purpose |
|---|---|
| `backend/app/services/processing/text_layout.py` | Text blocks, reading order, header/footer removal, garbled-text detection |
| `backend/app/services/processing/ocr.py` | Tesseract detection, OpenCV preprocessing, deskew, OCR |
| `backend/app/services/processing/tables.py` | pdfplumber tables → Markdown |
| `backend/app/services/processing/images.py` | Raster image and vector figure extraction |
| `backend/app/services/processing/extractor.py` | Combines everything for one PDF (no database code → easy to test) |
| `backend/app/services/processing/pipeline.py` | Background job: status updates, saving results, failure handling, restart recovery |
| `backend/app/api/v1/routes/documents.py` | New endpoints (below) |
| `frontend/src/pages/DocumentDetailPage.jsx` | Document viewer: page image + extracted text + tables + images |
| `backend/tests/pdf_factory.py` | Generates test PDFs in code (two-column, table, image, chart, scanned, encrypted) |

## New API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/documents/{id}/reprocess` | Run the pipeline again (202 Accepted) |
| GET | `/documents/{id}/pages` | Page list with extraction method and character count |
| GET | `/documents/{id}/pages/{n}` | Text of one page |
| GET | `/documents/{id}/pages/{n}/image?zoom=1.5` | Page rendered as PNG |
| GET | `/documents/{id}/elements?element_type=table&page=3` | Tables / images / figures |
| GET | `/documents/{id}/elements/{eid}/image` | The extracted picture |

## Installing Tesseract OCR (Windows) — needed for scanned PDFs

1. Download the installer from the UB Mannheim build: https://github.com/UB-Mannheim/tesseract/wiki
2. Run it. On the "Choose Components" screen expand **Additional language data** and tick **Telugu** if you want Telugu OCR.
3. Keep the default path `C:\Program Files\Tesseract-OCR\` (the app finds it automatically).
4. To enable Telugu OCR add to `backend/.env`: `OCR_LANGUAGES=eng+tel`
5. Restart uvicorn and reprocess any scanned document.

Without Tesseract everything still works; scanned pages are marked "Scanned (OCR not installed)" and the document shows a warning.

## How to run and test

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt      # large: PyTorch, Transformers, ChromaDB...
alembic upgrade head
pytest -v                            # 43 passed, 1 skipped (OCR test runs once Tesseract is installed)
uvicorn app.main:app --reload
```

In the browser: upload a research paper → watch the progress bar → status becomes **Ready** → click the title to open the document viewer → step through pages, compare the page image with the extracted text, check tables and figures.

**Sample request**
```http
GET /api/v1/documents/1/elements?element_type=table
Authorization: Bearer <token>
```
```json
[{"id": 4, "page_number": 6, "element_type": "table",
  "content": "| Model | BLEU |\n| --- | --- |\n| Transformer | 28.4 |",
  "bbox": [72.0, 410.5, 540.2, 520.0], "extra": {"rows": 2, "cols": 2}, "has_image": false}]
```

## Common errors

| Problem | Cause / fix |
|---|---|
| Status stays "uploaded" forever | uvicorn was restarted mid-job. On the next start it is marked failed → click **Reprocess**. |
| "Password-protected PDFs are not supported" | Remove the password (e.g. print to PDF) and upload again. |
| Scanned pages show no text | Tesseract not installed (see above). |
| Telugu OCR gives English-looking garbage | Telugu language data not installed or `OCR_LANGUAGES` not set to `eng+tel`. |
| A table is missing | pdfplumber finds tables from ruling lines. Tables without lines are still in the page text. |
| Columns are mixed up | Unusual layouts (3 columns, sidebars) are beyond the two-column heuristic; the text is still searchable. |

## Interview questions
1. How do you extract text from a PDF, and why is reading order a problem?
2. How do you detect a scanned PDF? What do you do with it?
3. What image preprocessing improves OCR, and why?
4. Explain Otsu's thresholding and the projection-profile deskew method.
5. What is the difference between raster images and vector graphics in a PDF? How do you extract each?
6. Why process documents in a background job? What are the limits of FastAPI BackgroundTasks, and when would you move to Celery + Redis?
7. How do you make a processing job idempotent and recover from crashes?
8. Why store tables as Markdown rather than plain text?
9. Why use MEDIUMTEXT in MySQL for page text?
10. Why did your Alembic downgrade fail on MySQL and how did you fix it? (Index needed by a foreign key; non-transactional DDL left a half-applied state.)
