"""Build the evaluation PDFs from datasets/corpus.yaml (deterministic: same input, same PDFs).

Usage (from the repository root):
    backend\\.venv\\Scripts\\python evaluation\\build_corpus.py
"""

from pathlib import Path

import pymupdf
import yaml

ROOT = Path(__file__).resolve().parent
CORPUS_YAML = ROOT / "datasets" / "corpus.yaml"
OUT_DIR = ROOT / "datasets" / "corpus"

LEFT, RIGHT, TOP, BOTTOM_MARGIN = 60, 535, 70, 70
FONT_SIZE = 10.5
GAP = 8


class Writer:
    """Writes blocks top to bottom on one page and fails loudly if text overflows."""

    def __init__(self, page: pymupdf.Page):
        self.page = page
        self.y = TOP

    def text(self, text: str, size: float = FONT_SIZE, gap: float = GAP) -> None:
        rect = pymupdf.Rect(LEFT, self.y, RIGHT, self.page.rect.height - BOTTOM_MARGIN)
        unused = self.page.insert_textbox(rect, text, fontsize=size, fontname="helv")
        if unused < 0:
            raise ValueError(f"Text does not fit on page {self.page.number + 1}: {text[:60]}...")
        self.y += rect.height - unused + gap

    def table(self, rows: list[list[str]]) -> None:
        widths = [max(len(row[c]) for row in rows) + 4 for c in range(len(rows[0]))]
        scale = (RIGHT - LEFT) / sum(widths)
        xs = [LEFT]
        for width in widths:
            xs.append(xs[-1] + width * scale)
        row_height = 18
        ys = [self.y + i * row_height for i in range(len(rows) + 1)]
        for x in xs:
            self.page.draw_line((x, ys[0]), (x, ys[-1]), width=0.6)
        for y in ys:
            self.page.draw_line((xs[0], y), (xs[-1], y), width=0.6)
        for r, row in enumerate(rows):
            for c, cell in enumerate(row):
                self.page.insert_text((xs[c] + 4, ys[r] + 12.5), cell, fontsize=9, fontname="hebo" if r == 0 else "helv")
        self.y = ys[-1] + GAP

    def chart(self, values: list[float]) -> None:
        """A vector bar chart, like the plots in research papers (no embedded image)."""
        x0, height, bar, step = LEFT + 40, 150, 34, 52
        base = self.y + height
        self.page.draw_line((x0, base), (x0 + step * len(values) + 10, base), width=0.8)
        self.page.draw_line((x0, base), (x0, self.y), width=0.8)
        for i, value in enumerate(values):
            left = x0 + 12 + i * step
            top = base - height * value / max(values)
            self.page.draw_rect(pymupdf.Rect(left, top, left + bar, base), color=(0.1, 0.3, 0.7), fill=(0.35, 0.55, 0.9))
            self.page.insert_text((left + 6, base + 12), str(200 * i), fontsize=7)
        self.y = base + 22


def build_document(spec: dict) -> bytes:
    pdf = pymupdf.open()
    pdf.set_metadata({"title": spec["title"]})
    for number, page_spec in enumerate(spec["pages"], start=1):
        page = pdf.new_page()  # A4
        # Running header and footer on every page: the pipeline should strip these.
        page.insert_textbox(pymupdf.Rect(LEFT, 25, RIGHT, 45), "DocuMind Evaluation Corpus", fontsize=8, fontname="helv")
        page.insert_textbox(
            pymupdf.Rect(LEFT, page.rect.height - 40, RIGHT, page.rect.height - 22), f"Page {number}", fontsize=8
        )
        writer = Writer(page)
        if number == 1:
            writer.text(spec["title"], size=17, gap=14)
        for paragraph in page_spec.get("paragraphs", []):
            writer.text(paragraph)
        if table := page_spec.get("table"):
            writer.text(table["caption"], size=9.5, gap=4)
            writer.table(table["rows"])
        if chart := page_spec.get("chart"):
            writer.chart(chart["values"])
            writer.text(chart["caption"], size=9.5)
        if references := page_spec.get("references"):
            writer.text("References", size=12, gap=4)
            for reference in references:
                writer.text(reference, size=8.5, gap=3)
    data = pdf.tobytes(garbage=3, deflate=True)
    pdf.close()
    return data


def main() -> None:
    spec = yaml.safe_load(CORPUS_YAML.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for document in spec["documents"]:
        (OUT_DIR / document["file"]).write_bytes(build_document(document))
        print(f"built {document['file']} ({len(document['pages'])} pages)")


if __name__ == "__main__":
    main()
