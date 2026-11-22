import pytest

from app.services.chunking.chunker import (
    ElementInput,
    PageInput,
    chunk_document,
    pack,
    split_sentences,
    split_text,
    strip_references,
)


def count(text: str) -> int:
    return len(text.split())


def tokenize(text: str) -> list[int]:
    return list(range(count(text)))


def chunk(pages, elements=(), strategy="recursive", size=50, overlap=10, skip_references=True):
    return chunk_document(
        pages,
        list(elements),
        strategy=strategy,
        count=count,
        tokenize=tokenize,
        size=size,
        overlap=overlap,
        skip_references=skip_references,
    )


LONG_TEXT = " ".join(f"Sentence number {i} explains a different idea about learning." for i in range(60))


def test_pack_carries_overlap_into_next_chunk():
    chunks = pack(["a b c", "d e", "f g h"], count, size=5, overlap=2)

    assert chunks == ["a b c d e", "d e f g h"]


@pytest.mark.parametrize("strategy", ["fixed", "recursive", "sentence"])
def test_every_strategy_respects_chunk_size(strategy):
    chunks = split_text(LONG_TEXT, strategy, count, tokenize, size=40, overlap=8)

    assert len(chunks) > 5
    assert all(count(c) <= 40 for c in chunks)
    # Nothing is lost: every sentence appears in some chunk
    assert all(f"number {i} " in " ".join(chunks) for i in range(60))


def test_recursive_strategy_keeps_sentences_whole():
    chunks = split_text(LONG_TEXT, "recursive", count, tokenize, size=40, overlap=8)

    for text in chunks:
        assert text.startswith("Sentence number") and text.endswith("learning.")


def test_sentence_splitting():
    text = "Models such as BERT, e.g. the base model, work well. Accuracy rose to 91%! ఇది తెలుగు వాక్యం. Next one?"

    assert split_sentences(text) == [
        "Models such as BERT, e.g. the base model, work well.",
        "Accuracy rose to 91%!",
        "ఇది తెలుగు వాక్యం.",
        "Next one?",
    ]


def test_references_section_is_removed_only_in_second_half():
    pages = [
        PageInput(1, "Introduction\n\nWe cite many References here."),
        PageInput(2, "Method text."),
        PageInput(3, "Conclusion text.\n\nREFERENCES\n\n[1] Vaswani et al. 2017."),
        PageInput(4, "[2] Devlin et al. 2019."),
    ]

    kept = strip_references(pages)

    assert [p.page_number for p in kept] == [1, 2, 3]
    assert kept[2].text == "Conclusion text."


def test_chunks_stay_on_their_page_and_are_ordered():
    pages = [PageInput(1, LONG_TEXT), PageInput(2, "Short second page about attention mechanisms.")]

    drafts = chunk(pages)

    assert {d.page_number for d in drafts} == {1, 2}
    assert [d.page_number for d in drafts] == sorted(d.page_number for d in drafts)
    assert drafts[-1].text == "Short second page about attention mechanisms."
    assert all(d.token_count == count(d.text) for d in drafts)


def test_large_table_is_split_with_header_repeated():
    rows = "\n".join(f"| model{i} | {i}.0 |" for i in range(40))
    table = ElementInput(7, 3, "table", f"| Model | Score |\n| --- | --- |\n{rows}")

    drafts = [d for d in chunk([], [table], size=60) if d.element_type == "table"]

    assert len(drafts) > 1
    for draft in drafts:
        assert draft.text.startswith("Table (page 3):\n| Model | Score |\n| --- | --- |")
        assert draft.element_id == 7


def test_figures_are_chunked_only_once_described():
    elements = [ElementInput(1, 2, "figure", ""), ElementInput(2, 2, "figure", "Bar chart of loss falling over epochs.")]

    drafts = chunk([], elements)

    assert [d.text for d in drafts] == ["Figure (page 2): Bar chart of loss falling over epochs."]
