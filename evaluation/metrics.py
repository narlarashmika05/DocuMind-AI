"""Evaluation metrics. Relevance is judged at PAGE level: a retrieved chunk is relevant
if its (document, page) is one of the question's gold pages. This makes the ground
truth independent of the chunking strategy, so strategies can be compared fairly."""

from collections.abc import Sequence
from statistics import mean

Page = tuple[str, int]


def precision_at_k(retrieved: Sequence[Page], gold: set[Page], k: int) -> float:
    """Share of the top-k results that are relevant."""
    top = retrieved[:k]
    return sum(page in gold for page in top) / k if k else 0.0


def recall_at_k(retrieved: Sequence[Page], gold: set[Page], k: int) -> float:
    """Share of the gold pages found in the top-k results."""
    return len(set(retrieved[:k]) & gold) / len(gold) if gold else 0.0


def hit_at_k(retrieved: Sequence[Page], gold: set[Page], k: int) -> float:
    return 1.0 if set(retrieved[:k]) & gold else 0.0


def reciprocal_rank(retrieved: Sequence[Page], gold: set[Page]) -> float:
    """1 / rank of the first relevant result (0 if none). Averaged over queries = MRR."""
    for rank, page in enumerate(retrieved, start=1):
        if page in gold:
            return 1.0 / rank
    return 0.0


def retrieval_scores(retrieved: Sequence[Page], gold: set[Page], k_values: Sequence[int]) -> dict[str, float]:
    scores = {"mrr": reciprocal_rank(retrieved, gold)}
    for k in k_values:
        scores[f"precision@{k}"] = precision_at_k(retrieved, gold, k)
        scores[f"recall@{k}"] = recall_at_k(retrieved, gold, k)
        scores[f"hit@{k}"] = hit_at_k(retrieved, gold, k)
    return scores


def average(rows: list[dict[str, float]]) -> dict[str, float]:
    return {key: round(mean(row[key] for row in rows), 4) for key in rows[0]} if rows else {}


def percentile(values: Sequence[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, round(q * (len(ordered) - 1)))
    return ordered[index]


def binary_classification(gold: Sequence[bool], predicted: Sequence[bool]) -> dict[str, float]:
    """Precision/recall/F1 where True = 'hallucination flagged'."""
    tp = sum(g and p for g, p in zip(gold, predicted))
    fp = sum(p and not g for g, p in zip(gold, predicted))
    fn = sum(g and not p for g, p in zip(gold, predicted))
    tn = sum(not g and not p for g, p in zip(gold, predicted))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round((tp + tn) / len(gold), 4) if gold else 0.0,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }
