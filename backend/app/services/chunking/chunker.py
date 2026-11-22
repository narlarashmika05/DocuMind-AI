"""Split document content into chunks: the passages that get embedded, retrieved and cited.

Why chunk at all? Embedding models read at most a few hundred tokens, and a focused
passage matches a question better than a whole page. Chunks never cross a page
boundary, so every answer can cite an exact page.

Strategies (compared in Module 9):
- fixed:     windows of N tokens, ignoring sentences (simple baseline)
- recursive: paragraphs -> sentences -> words, packed up to N tokens (default)
- sentence:  LlamaIndex SentenceSplitter
"""

import re
from collections.abc import Callable
from dataclasses import dataclass

TokenCounter = Callable[[str], int]
Tokenizer = Callable[[str], list[int]]

STRATEGIES = ("fixed", "recursive", "sentence")

# Split after . ! ? (or the Devanagari danda) when the next sentence starts with a capital,
# a digit or a Telugu character. "e.g. the" is not split because "the" is lowercase.
SENTENCE_END = re.compile(r"(?<=[.!?।])\s+(?=[\"'(\[]?[A-Z0-9ఀ-౿])")
REFERENCES_HEADING = re.compile(r"^(\d+\.?\s*)?(references|bibliography|works cited|literature cited)\s*$", re.I)
MIN_CHUNK_CHARS = 20


@dataclass
class PageInput:
    page_number: int
    text: str


@dataclass
class ElementInput:
    id: int
    page_number: int
    element_type: str
    content: str


@dataclass
class ChunkDraft:
    text: str
    page_number: int
    element_type: str = "text"  # text | table | figure | image
    element_id: int | None = None
    token_count: int = 0


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_END.split(text) if s.strip()]


def strip_references(pages: list[PageInput]) -> list[PageInput]:
    """Drop the bibliography: everything from a "References" heading in the second half onwards."""
    for index in range(len(pages) // 2, len(pages)):
        paragraphs = pages[index].text.split("\n\n")
        for p_index, paragraph in enumerate(paragraphs):
            if REFERENCES_HEADING.match(paragraph.strip()):
                kept = PageInput(pages[index].page_number, "\n\n".join(paragraphs[:p_index]))
                return pages[:index] + ([kept] if kept.text.strip() else [])
    return pages


def pack(units: list[str], count: TokenCounter, size: int, overlap: int) -> list[str]:
    """Greedily fill chunks with units up to `size` tokens.

    When a chunk is full, the next one starts with the last units of the previous one
    (up to `overlap` tokens), so an idea split across the boundary appears whole in
    at least one chunk.
    """
    chunks: list[str] = []
    current: list[tuple[str, int]] = []
    current_tokens = 0
    for unit in units:
        tokens = count(unit)
        if current and current_tokens + tokens > size:
            chunks.append(" ".join(text for text, _ in current))
            carried: list[tuple[str, int]] = []
            carried_tokens = 0
            for text, n in reversed(current):
                if carried_tokens + n > overlap:
                    break
                carried.insert(0, (text, n))
                carried_tokens += n
            current, current_tokens = carried, carried_tokens
        current.append((unit, tokens))
        current_tokens += tokens
    if current:
        chunks.append(" ".join(text for text, _ in current))
    return chunks


def _recursive_units(text: str, count: TokenCounter, size: int) -> list[str]:
    units = []
    for paragraph in (p.strip() for p in text.split("\n\n")):
        if not paragraph:
            continue
        if count(paragraph) <= size:
            units.append(paragraph)
            continue
        for sentence in split_sentences(paragraph):
            units.extend([sentence] if count(sentence) <= size else sentence.split())
    return units


def split_text(
    text: str,
    strategy: str,
    count: TokenCounter,
    tokenize: Tokenizer,
    size: int,
    overlap: int,
) -> list[str]:
    if strategy == "fixed":
        return pack(text.split(), count, size, overlap)
    if strategy == "recursive":
        return pack(_recursive_units(text, count, size), count, size, overlap)
    if strategy == "sentence":
        from llama_index.core.node_parser import SentenceSplitter

        splitter = SentenceSplitter(
            chunk_size=size, chunk_overlap=overlap, tokenizer=tokenize, paragraph_separator="\n\n"
        )
        return splitter.split_text(text)
    raise ValueError(f"Unknown chunk strategy '{strategy}'. Choose one of: {', '.join(STRATEGIES)}")


def _table_chunks(element: ElementInput, count: TokenCounter, size: int) -> list[str]:
    """Large tables are split by rows; every part repeats the header so it stays understandable."""
    label = f"Table (page {element.page_number}):\n"
    lines = element.content.splitlines()
    if count(label + element.content) <= size or len(lines) <= 3:
        return [label + element.content]
    header, rows = lines[:2], lines[2:]
    parts, current = [], []
    for row in rows:
        if current and count(label + "\n".join(header + current + [row])) > size:
            parts.append(label + "\n".join(header + current))
            current = []
        current.append(row)
    parts.append(label + "\n".join(header + current))
    return parts


def chunk_document(
    pages: list[PageInput],
    elements: list[ElementInput],
    *,
    strategy: str,
    count: TokenCounter,
    tokenize: Tokenizer,
    size: int,
    overlap: int,
    skip_references: bool = True,
) -> list[ChunkDraft]:
    if skip_references:
        pages = strip_references(pages)

    drafts: list[ChunkDraft] = []
    for page in pages:
        for text in split_text(page.text, strategy, count, tokenize, size, overlap):
            if len(text) >= MIN_CHUNK_CHARS:
                drafts.append(ChunkDraft(text, page.page_number))

    for element in elements:
        if element.element_type == "table":
            texts = _table_chunks(element, count, size)
        elif element.content.strip():  # images/figures are searchable once described (Module 7)
            texts = [f"{element.element_type.capitalize()} (page {element.page_number}): {element.content.strip()}"]
        else:
            continue
        drafts.extend(ChunkDraft(text, element.page_number, element.element_type, element.id) for text in texts)

    drafts.sort(key=lambda d: (d.page_number, d.element_type != "text"))
    for draft in drafts:
        draft.token_count = count(draft.text)
    return drafts
