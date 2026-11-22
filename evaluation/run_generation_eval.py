"""End-to-end answer evaluation with Gemini (needs GEMINI_API_KEY in backend/.env).

Metrics (RAGAS-style definitions, computed locally and deterministically):
  faithfulness        share of answer claims the NLI verifier marks supported
  hallucination_rate  share of claims marked unsupported or contradicted
  answer_relevance    cosine similarity between the question and the answer (multilingual-E5)
  answer_similarity   cosine similarity between the answer and the reference answer
  context_recall      did the passages given to the LLM include a gold page?
  abstention          unanswerable questions answered with "insufficient information"
  latency             seconds per question (retrieval + generation + verification)

Why not the ragas package itself? It needs an extra judge-LLM call per metric (free-tier quota),
its results vary between runs, and its API changes often. These local versions follow the same
definitions; see docs/modules/module-09-evaluation.md.

Usage:
    backend\\.venv\\Scripts\\python evaluation\\run_generation_eval.py --limit 10 --languages en te
"""

import argparse
import time
from statistics import mean
from types import SimpleNamespace

import numpy as np

from common import RESULTS_DIR, EvalIndex, extract_corpus, load_jsonl, timestamp, write_json

from app.core.config import settings
from app.services.embeddings.encoder import get_embedder
from app.services.llm import prompts
from app.services.llm.client import LLMError, get_llm
from app.services.retrieval.reranker import get_reranker
from app.services.verification.verifier import verify_claims


def cosine(embedder, a: str, b: str) -> float:
    va, vb = (np.asarray(embedder.embed_query(t)) for t in (a, b))
    return float(va @ vb)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="number of questions (free-tier friendly)")
    parser.add_argument("--languages", nargs="+", default=["en", "te"])
    parser.add_argument("--delay", type=float, default=4.0, help="seconds between questions (rate limit)")
    args = parser.parse_args()

    llm = get_llm()  # fails with a clear message when no key is configured
    questions = load_jsonl("qa.jsonl")[: args.limit]
    docs = extract_corpus()
    titles = {d.file: d.title for d in docs}
    embedder = get_embedder("multilingual-e5-base")
    index = EvalIndex(docs, embedder, "recursive", 300, 50)
    reranker = get_reranker()

    rows = []
    for language in args.languages:
        for q in questions:
            question = q["question_te"] if language == "te" else q["question_en"]
            started = time.perf_counter()
            try:
                english = q["question_en"]
                if language == "te":  # same translation step as the app
                    english = llm.generate_json(prompts.QUERY_SYSTEM, prompts.query_prompt([], question),
                                                prompts.PreparedQuery, temperature=0.0).standalone_question_en
                results = [r for r in index.search(question, english, "hybrid", reranker, settings.RAG_TOP_K)
                           if r.score >= settings.RELEVANCE_THRESHOLD]
                status, claims, checks = "insufficient_information", [], []
                if results:
                    sources = [SimpleNamespace(number=i, chunk=r.chunk) for i, r in enumerate(results, start=1)]
                    formatted = [prompts.format_source(s.number, titles[s.chunk.document], s.chunk.page,
                                                       s.chunk.element_type, s.chunk.text, False) for s in sources]
                    answer = llm.generate_json(prompts.answer_system_prompt(language),
                                               prompts.answer_prompt(formatted, [], english, question), prompts.GeneratedAnswer)
                    status, claims = answer.status, [c for c in answer.claims if c.text.strip()]
                    if status == "answered" and claims:
                        checks = verify_claims([c.text for c in claims], [c.citations for c in claims], sources)
            except LLMError as exc:
                print(f"  {q['id']} {language}: LLM error: {exc}")
                continue
            seconds = time.perf_counter() - started
            answer_text = " ".join(c.text for c in claims)
            answerable = q["type"] != "unanswerable"
            row = {
                "id": q["id"], "language": language, "answerable": answerable, "status": status,
                "seconds": round(seconds, 2), "answer": answer_text,
                "context_recall": float(any((r.chunk.document, r.chunk.page) in {(q["document"], p) for p in q["pages"]}
                                            for r in results)) if answerable else None,
            }
            if checks:
                row["faithfulness"] = mean(c.score for c in checks)
                row["hallucination_rate"] = mean(c.verdict in ("unsupported", "contradicted") for c in checks)
            if answer_text and answerable:
                row["answer_relevance"] = round(cosine(embedder, q["question_en"], answer_text), 4)
                row["answer_similarity"] = round(cosine(embedder, q["answer"], answer_text), 4)
            rows.append(row)
            print(f"  {q['id']} {language} {status:24s} {seconds:5.1f}s faith={row.get('faithfulness')}")
            time.sleep(args.delay)

    def avg(key, subset):
        values = [r[key] for r in subset if r.get(key) is not None]
        return round(mean(values), 4) if values else None

    summary = []
    for language in args.languages:
        subset = [r for r in rows if r["language"] == language]
        answerable = [r for r in subset if r["answerable"]]
        unanswerable = [r for r in subset if not r["answerable"]]
        summary.append({
            "language": language,
            "questions": len(subset),
            "faithfulness": avg("faithfulness", subset),
            "hallucination_rate": avg("hallucination_rate", subset),
            "answer_relevance": avg("answer_relevance", subset),
            "answer_similarity": avg("answer_similarity", subset),
            "context_recall": avg("context_recall", answerable),
            "answered_rate_answerable": round(mean(r["status"] == "answered" for r in answerable), 4) if answerable else None,
            "abstention_unanswerable": round(mean(r["status"] != "answered" for r in unanswerable), 4) if unanswerable else None,
            "latency_s_mean": avg("seconds", subset),
        })

    run_name = f"generation_{timestamp()}"
    out_dir = RESULTS_DIR / run_name
    write_json(out_dir / "results.json", {"kind": "generation", "name": run_name, "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                                          "model": settings.GEMINI_MODEL, "summary": summary, "rows": rows})
    for row in summary:
        print(row)
    print(f"Results written to {out_dir}")


if __name__ == "__main__":
    main()
