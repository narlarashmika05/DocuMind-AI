"""The embedding models this project supports and compares (Modules 4, 6 and 9).

An embedding model turns text into a vector (a list of numbers) so that texts with
similar meaning get vectors that point in similar directions.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingModelSpec:
    key: str
    hf_name: str  # Hugging Face model id
    dimensions: int
    max_tokens: int  # longer input is silently truncated by the model
    multilingual: bool
    size_mb: int
    # E5 models were trained with these prefixes and work noticeably worse without them.
    query_prefix: str = ""
    passage_prefix: str = ""


EMBEDDING_MODELS: dict[str, EmbeddingModelSpec] = {
    spec.key: spec
    for spec in [
        # English-only baseline: small and fast, but cannot match Telugu questions to English text.
        EmbeddingModelSpec("minilm-en", "sentence-transformers/all-MiniLM-L6-v2", 384, 256, False, 90),
        # Smaller sibling of the default: same training recipe, 384 dimensions, ~2.5x faster on CPU.
        EmbeddingModelSpec(
            "multilingual-e5-small",
            "intfloat/multilingual-e5-small",
            384,
            512,
            True,
            470,
            query_prefix="query: ",
            passage_prefix="passage: ",
        ),
        # Default: XLM-RoBERTa based, trained on ~100 languages including Telugu.
        EmbeddingModelSpec(
            "multilingual-e5-base",
            "intfloat/multilingual-e5-base",
            768,
            512,
            True,
            1100,
            query_prefix="query: ",
            passage_prefix="passage: ",
        ),
        # Strongest multilingual option here, but 2.2 GB and slower on CPU.
        EmbeddingModelSpec("bge-m3", "BAAI/bge-m3", 1024, 8192, True, 2200),
    ]
}


def get_spec(key: str) -> EmbeddingModelSpec:
    try:
        return EMBEDDING_MODELS[key]
    except KeyError:
        raise ValueError(f"Unknown embedding model '{key}'. Choose one of: {', '.join(EMBEDDING_MODELS)}") from None
