# Module 7 – Multimodal Document Understanding

## Objective
Make charts, diagrams, images, tables and scanned pages **searchable and answerable**, while keeping references to the original page.

## Concepts

### Multimodal AI
A multimodal model processes more than one kind of input — here text **and** images. Vision-language models (like Gemini) encode an image into a sequence of visual tokens (a Vision Transformer splits the image into patches and embeds each patch), then the language model attends to those tokens together with the text tokens.

### How each kind of content is handled
| Content | Extraction (Module 3) | Made searchable by | Answering |
|---|---|---|---|
| Normal text | PyMuPDF text layer | text chunks | cited passage |
| Scanned page | OpenCV + Tesseract OCR | OCR text chunks | cited passage |
| Table | pdfplumber → Markdown | table chunks (header repeated when split) | Markdown table rendered in the source panel |
| Raster image (photo, screenshot, scanned chart) | PyMuPDF image → PNG | **Gemini vision description** → figure chunk | description + **the image itself attached to the answer prompt** |
| Vector chart/diagram | drawing clusters rendered → PNG | **Gemini vision description** → figure chunk | same as above |

### Two-stage multimodal design
1. **Ingestion (describe once):** every extracted picture is sent once to Gemini vision with a prompt asking for visual type, title/caption, axes, units, legend, key values, trends and visible text — "never invent values". Captions found on the same page ("Figure 3: …") are included as hints. The description becomes the element's `content` and is chunked: `Figure (page 4): Line plot: validation loss decreases from 2.1 to 0.4 …`.
2. **Answering (look again):** when a figure chunk is retrieved, the **actual PNG** is attached to the generation call (max 3 images), so the model can read exact values instead of relying only on the description.

Why not send every page image to the LLM for every question? Cost, latency and rate limits. Describing once and retrieving by text is far cheaper.

### Free-tier protection
Only the largest 15 pictures per document are described, with a 4-second pause between calls. On a rate-limit error the remaining figures are skipped and the user sees a processing note. Without an API key, figures fall back to OCR of their text (if Tesseract is installed).

### OCR vs vision model
| | Tesseract OCR | Vision LLM |
|---|---|---|
| Reads printed text | ✔ precise, offline, free | ✔ |
| Understands a chart's meaning | ✘ | ✔ |
| Cost / privacy | free, local | API quota, data leaves the machine |
So OCR is used for scanned **text**, the vision model for **visual meaning**.

### Preserving page references
Every element stores `page_number` and `bbox`; figure chunks carry `element_id`. Citations therefore show the figure image, the page number and a rendered page image, and link to the viewer at that page.

## Files
| File | Purpose |
|---|---|
| `app/services/processing/images.py` | Raster images + vector figure detection (Module 3) |
| `app/services/processing/tables.py` | Tables → Markdown (Module 3) |
| `app/services/multimodal/figures.py` | `describe_figures` (ingestion) and `load_figure_images` (answering) |
| `app/services/processing/pipeline.py` | "describing" stage between extraction and chunking |
| `frontend/src/components/chat/SourcePanel.jsx` | Shows figure image / table / page image for each citation |
| `frontend/src/pages/DocumentDetailPage.jsx` | Shows extracted figures with their descriptions |

## Test
```powershell
pytest tests/test_chat.py -k figure -v
```
UI: upload a paper with charts → open it in the viewer → figures show their generated descriptions → ask "What does Figure 2 show?" → the citation is a figure and its image appears in the source panel.

## Limitations
- Very dense charts may be described imprecisely; exact values come from the attached image at answer time, but can still be misread.
- Vector-figure detection is heuristic (clusters of drawings); unusual layouts can produce partial or merged figures.
- Tables without ruling lines are not detected as tables (their text is still in the page text).
- Figure descriptions use the API quota; very image-heavy documents are only partly described on the free tier.

## Interview questions
1. What makes a model multimodal? How does a vision transformer turn an image into tokens?
2. Why describe figures at ingestion time instead of sending page images with every question?
3. OCR vs vision-language model — when do you use which?
4. How do you extract vector charts from a PDF?
5. How do you keep citations pointing to the right page for images and tables?
6. How would you evaluate figure-question answering?
