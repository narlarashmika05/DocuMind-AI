"""Table extraction with pdfplumber, converted to Markdown.

Markdown keeps rows and columns readable for both humans and the LLM, so a question
like "what was the accuracy of model B?" can be answered from the right cell.
"""

from dataclasses import dataclass

import pdfplumber.page


@dataclass
class ExtractedTable:
    markdown: str
    bbox: list[float]
    n_rows: int
    n_cols: int


def _clean_cell(cell: str | None) -> str:
    return " ".join((cell or "").split()).replace("|", "\\|")


def rows_to_markdown(rows: list[list[str | None]]) -> tuple[str, int, int]:
    cleaned = [[_clean_cell(cell) for cell in row] for row in rows]
    cleaned = [row for row in cleaned if any(row)]  # drop empty rows
    if not cleaned:
        return "", 0, 0

    n_cols = max(len(row) for row in cleaned)
    cleaned = [row + [""] * (n_cols - len(row)) for row in cleaned]
    keep = [c for c in range(n_cols) if any(row[c] for row in cleaned)]  # drop empty columns
    cleaned = [[row[c] for c in keep] for row in cleaned]
    if not keep:
        return "", 0, 0

    header, *body = cleaned
    header = [cell or f"Column {i + 1}" for i, cell in enumerate(header)]
    lines = ["| " + " | ".join(header) + " |", "|" + " --- |" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in body]
    return "\n".join(lines), len(cleaned), len(keep)


def extract_tables(page: pdfplumber.page.Page) -> list[ExtractedTable]:
    tables = []
    for table in page.find_tables():
        markdown, n_rows, n_cols = rows_to_markdown(table.extract())
        if n_rows >= 2 and n_cols >= 2:  # a 1-row or 1-column "table" is usually a ruled box
            tables.append(ExtractedTable(markdown, [round(v, 1) for v in table.bbox], n_rows, n_cols))
    return tables
