"""Retrieval evaluation: embedding models, chunking strategies, retrieval modes,
English vs Telugu questions, and the relevance gate.

Usage (from the repository root; downloads models on first run):
    backend\\.venv\\Scripts\\python evaluation\\run_retrieval_eval.py
    backend\\.venv\\Scripts\\python evaluation\\run_retrieval_eval.py --config evaluation/configs/retrieval.yaml --quick
"""

import argparse
import itertools
import time

import yaml

from common import RESULTS_DIR, ROOT, EvalIndex, extract_corpus, load_jsonl, timestamp, write_json
from metrics import average, percentile, retrieval_scores
from report import write_retrieval_report

from app.services.embeddings.encoder import get_embedder
from app.services.retrieval.reranker import get_reranker


def queries_for(question: dict, language: str) -> tuple[str, str]:
    """(query for dense search, query for BM25 + reranker)."""
    if language == "en":
        return question["question_en"], question["question_en"]
    if language == "te":
        return question["question_te"], question["question_en"]
    if language == "te_raw":
        return question["question_te"], question["question_te"]
    raise ValueError(language)


def evaluate(index: EvalIndex, questions, mode, language, reranker, config) -> tuple[dict, list[dict]]:
    per_query, rows, latencies = [], [], []
    for q in questions:
        dense_query, english_query = queries_for(q, language)
        started = time.perf_counter()
        results = index.search(dense_query, english_query, mode, reranker, config["top_k"], config["candidates"])
        latencies.append((time.perf_counter() - started) * 1000)
        retrieved = [r.chunk.page_key for r in results]
        gold = {(q["document"], page) for page in q["pages"]}
        scores = retrieval_scores(retrieved, gold, config["k_values"])
        rows.append(scores)
        per_query.append({"id": q["id"], "type": q["type"], **{k: round(v, 4) for k, v in scores.items()},
                          "top_page": f"{retrieved[0][0]}#p{retrieved[0][1]}" if retrieved else None})
    summary = average(rows)
    summary["latency_ms_mean"] = round(sum(latencies) / len(latencies), 1)
    summary["latency_ms_p95"] = round(percentile(latencies, 0.95), 1)
    return summary, per_query


def gate_sweep(index: EvalIndex, questions, reranker, config) -> list[dict]:
    """Best reranker score per question -> answer/refuse decision at each threshold."""
    best = []
    for q in questions:
        for language in ("en", "te"):
            dense_query, english_query = queries_for(q, language)
            results = index.search(dense_query, english_query, config["gate"]["mode"], reranker, 5, config["candidates"])
            best.append((q["type"] != "unanswerable", results[0].score if results else 0.0))
    rows = []
    for threshold in config["gate"]["thresholds"]:
        answerable = [score >= threshold for is_answerable, score in best if is_answerable]
        refused = [score < threshold for is_answerable, score in best if not is_answerable]
        rows.append({
            "threshold": threshold,
            "answerable_answered": round(sum(answerable) / len(answerable), 4),
            "unanswerable_refused": round(sum(refused) / len(refused), 4),
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(ROOT / "configs" / "retrieval.yaml"))
    parser.add_argument("--quick", action="store_true", help="first 10 answerable questions only (smoke test)")
    args = parser.parse_args()

    config = yaml.safe_load(open(args.config, encoding="utf-8"))
    questions = load_jsonl("qa.jsonl")
    answerable = [q for q in questions if q["type"] != "unanswerable"]
    if args.quick:
        answerable = answerable[:10]

    print("Extracting corpus...")
    docs = extract_corpus()
    reranker = get_reranker()
    indexes: dict[tuple[str, str, int], EvalIndex] = {}

    def index_for(model: str, strategy: str, size: int | None = None) -> EvalIndex:
        size = size or config["chunk_size"]
        if (model, strategy, size) not in indexes:
            print(f"Indexing with {model} / {strategy} / {size} tokens...")
            overlap = min(config["chunk_overlap"], size // 4)  # keep overlap proportional for small chunks
            indexes[(model, strategy, size)] = EvalIndex(docs, get_embedder(model), strategy, size, overlap)
        return indexes[(model, strategy, size)]

    run_name = f"{config['name']}_{timestamp()}"
    results = {
        "kind": "retrieval",
        "name": run_name,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": config,
        "dataset": {"answerable": len(answerable), "unanswerable": len(questions) - len(answerable) if not args.quick else 0,
                    "documents": len(docs), "pages": sum(len(d.pages) for d in docs)},
        "experiments": {},
        "per_query": {},
    }

    for experiment in config["experiments"]:
        grid = experiment["grid"]
        rows = []
        sizes = grid.get("chunk_size", [config["chunk_size"]])
        for model, strategy, size, mode, rerank, language in itertools.product(
            grid["model"], grid["strategy"], sizes, grid["mode"], grid["rerank"], grid["language"]
        ):
            index = index_for(model, strategy, size)
            summary, per_query = evaluate(index, answerable, mode, language, reranker if rerank else None, config)
            setting = {"model": model, "strategy": strategy, "chunk_size": size, "mode": mode, "rerank": rerank,
                       "language": language, "chunks": len(index.chunks)}
            rows.append({**setting, **summary})
            results["per_query"][f"{experiment['name']}|{model}|{strategy}|{size}|{mode}|{rerank}|{language}"] = per_query
            print(f"  {experiment['name']:16s} {model:22s} {strategy:9s} {size:4d} {mode:7s} rerank={str(rerank):5s} {language:6s} "
                  f"MRR={summary['mrr']:.3f} R@5={summary['recall@5']:.3f} P@3={summary['precision@3']:.3f}")
        results["experiments"][experiment["name"]] = {"description": experiment["description"], "rows": rows}

    if not args.quick:
        gate = config["gate"]
        results["gate"] = gate_sweep(index_for(gate["model"], gate["strategy"]), questions, reranker, config)

    out_dir = RESULTS_DIR / run_name
    write_json(out_dir / "results.json", results)
    write_retrieval_report(results, out_dir)
    print(f"\nResults written to {out_dir}")


if __name__ == "__main__":
    main()
