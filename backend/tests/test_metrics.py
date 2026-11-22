import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "evaluation"))

from metrics import binary_classification, precision_at_k, recall_at_k, reciprocal_rank, retrieval_scores  # noqa: E402

GOLD = {("a.pdf", 2), ("a.pdf", 3)}
RETRIEVED = [("b.pdf", 1), ("a.pdf", 2), ("a.pdf", 2), ("c.pdf", 4), ("a.pdf", 3)]


def test_precision_counts_relevant_results_in_top_k():
    assert precision_at_k(RETRIEVED, GOLD, 1) == 0.0
    assert precision_at_k(RETRIEVED, GOLD, 3) == pytest.approx(2 / 3)
    assert precision_at_k(RETRIEVED, GOLD, 5) == pytest.approx(3 / 5)


def test_recall_counts_distinct_gold_pages_found():
    assert recall_at_k(RETRIEVED, GOLD, 3) == 0.5
    assert recall_at_k(RETRIEVED, GOLD, 5) == 1.0


def test_reciprocal_rank_uses_first_relevant_result():
    assert reciprocal_rank(RETRIEVED, GOLD) == 0.5
    assert reciprocal_rank([("x.pdf", 1)], GOLD) == 0.0


def test_retrieval_scores_include_every_k():
    scores = retrieval_scores(RETRIEVED, GOLD, [1, 3])
    assert set(scores) == {"mrr", "precision@1", "recall@1", "hit@1", "precision@3", "recall@3", "hit@3"}
    assert scores["hit@3"] == 1.0


def test_binary_classification():
    result = binary_classification([True, True, False, False], [True, False, True, False])
    assert (result["tp"], result["fp"], result["fn"], result["tn"]) == (1, 1, 1, 1)
    assert result["precision"] == result["recall"] == result["f1"] == 0.5


def test_evaluation_api_lists_and_returns_runs(client, make_user, tmp_path, monkeypatch):
    import json

    from app.core.config import settings

    run = tmp_path / "verifier_2026-01-01T00-00-00"
    run.mkdir()
    (run / "results.json").write_text(json.dumps({"name": run.name, "kind": "verifier", "created": "2026-01-01 00:00:00"}))
    monkeypatch.setattr(settings, "EVALUATION_RESULTS_DIR", tmp_path)
    headers = make_user()

    runs = client.get("/api/v1/evaluation/runs", headers=headers).json()
    assert runs == [{"name": run.name, "kind": "verifier", "created": "2026-01-01 00:00:00"}]
    assert client.get(f"/api/v1/evaluation/runs/{run.name}", headers=headers).json()["kind"] == "verifier"
    assert client.get("/api/v1/evaluation/runs/..%2F..%2Fsecret", headers=headers).status_code == 404
    assert client.get("/api/v1/evaluation/runs", headers={}).status_code == 401
