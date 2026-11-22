"""Evaluate the hallucination detector on labelled claims (no API key needed).

Each claim is checked against the chunks of its source page with the real NLI model,
exactly as the app checks answer claims.

Usage: backend\\.venv\\Scripts\\python evaluation\\run_verifier_eval.py
"""

import time
from collections import Counter
from types import SimpleNamespace

from common import RESULTS_DIR, extract_corpus, load_jsonl, timestamp, write_json
from metrics import binary_classification
from report import write_verifier_report

from app.services.chunking.chunker import chunk_document
from app.services.embeddings.encoder import get_embedder
from app.services.verification.verifier import verify_claims

VERDICTS = ["supported", "partially_supported", "unsupported", "contradicted", "not_checked"]


def main() -> None:
    claims = load_jsonl("claims.jsonl")
    docs = {d.file: d for d in extract_corpus()}
    embedder = get_embedder("multilingual-e5-base")  # tokenizer for chunking, as in the app

    predictions, started = [], time.perf_counter()
    for item in claims:
        doc = docs[item["document"]]
        page = [p for p in doc.pages if p.page_number == item["page"]]
        drafts = chunk_document(page, [e for e in doc.elements if e.page_number == item["page"]], strategy="recursive",
                                count=embedder.count_tokens, tokenize=embedder.tokenize, size=300, overlap=50)
        sources = [SimpleNamespace(number=i, chunk=SimpleNamespace(text=d.text)) for i, d in enumerate(drafts, start=1)]
        [check] = verify_claims([item["claim"]], [[s.number for s in sources]], sources)
        predictions.append(check)
        print(f"  {item['id']} gold={item['label']:13s} predicted={check.verdict:20s} {check.confidence}")
    seconds = time.perf_counter() - started

    gold_flags = [c["label"] != "supported" for c in claims]
    predicted_flags = [p.verdict in ("unsupported", "contradicted") for p in predictions]
    confusion = {label: {v: 0 for v in VERDICTS} for label in ("supported", "unsupported", "contradicted")}
    for item, prediction in zip(claims, predictions):
        confusion[item["label"]][prediction.verdict] += 1

    run_name = f"verifier_{timestamp()}"
    results = {
        "kind": "verifier",
        "name": run_name,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(claims),
        "label_counts": dict(Counter(c["label"] for c in claims)),
        "binary": binary_classification(gold_flags, predicted_flags),
        "three_class_accuracy": round(sum(c["label"] == p.verdict for c, p in zip(claims, predictions)) / len(claims), 4),
        "confusion": confusion,
        "seconds_per_claim": round(seconds / len(claims), 3),
        "errors": [
            {"id": c["id"], "gold": c["label"], "predicted": p.verdict, "confidence": p.confidence, "claim": c["claim"]}
            for c, p in zip(claims, predictions) if c["label"] != p.verdict
        ],
    }
    out_dir = RESULTS_DIR / run_name
    write_json(out_dir / "results.json", results)
    write_verifier_report(results, out_dir)
    print(f"\nPrecision {results['binary']['precision']}  Recall {results['binary']['recall']}  F1 {results['binary']['f1']}")
    print(f"Results written to {out_dir}")


if __name__ == "__main__":
    main()
