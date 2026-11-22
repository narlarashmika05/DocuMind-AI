# Evaluation framework

Reproducible experiments that measure DocuMind AI's retrieval, multilingual retrieval, relevance gate,
hallucination detector and (with a Gemini key) end-to-end answers. Results appear on the app's
**Evaluation** page and in `results/<run>/summary.md`.

## Contents
| Path | Purpose |
|---|---|
| `datasets/corpus.yaml` | Source text of 5 educational documents (15 pages: biology, ML paper review, geography, immunology, history) with tables, a vector chart, running headers/footers and a references section |
| `build_corpus.py` | Turns the YAML into PDFs (`datasets/corpus/`) deterministically |
| `datasets/qa.jsonl` | 41 questions, each in **English and Telugu**, with gold source pages and a reference answer: 35 answerable (text, table, figure) + 6 unanswerable (3 off-topic, 3 near-domain distractors) |
| `datasets/claims.jsonl` | 31 claims labelled supported / unsupported / contradicted against corpus pages |
| `configs/retrieval.yaml` | Experiment grid |
| `run_retrieval_eval.py` | Embedding models × languages, chunking strategies × sizes, retrieval modes × reranking, relevance-gate sweep |
| `run_verifier_eval.py` | Hallucination-detector precision/recall/confusion matrix |
| `run_generation_eval.py` | End-to-end answers with Gemini: faithfulness, hallucination rate, answer relevance, context recall, abstention, latency |
| `metrics.py`, `report.py` | Metric definitions; Markdown tables and charts |

## Run
From the repository root, with the backend virtual environment:
```powershell
backend\.venv\Scripts\python evaluation\build_corpus.py
backend\.venv\Scripts\python evaluation\run_retrieval_eval.py          # ~10-20 min on CPU
backend\.venv\Scripts\python evaluation\run_verifier_eval.py           # ~1 min
backend\.venv\Scripts\python evaluation\run_generation_eval.py --limit 20 --languages en te   # needs GEMINI_API_KEY
```
The evaluation reuses the application's own extraction, chunking, embedding, BM25, fusion, reranking and
verification code, but holds the index in memory — it never touches MySQL, ChromaDB or users' files.

## Methodology

**Relevance at page level.** A retrieved chunk is relevant if its (document, page) is a gold page for the question.
Page-level ground truth stays valid whatever the chunking strategy, so strategies can be compared fairly.

**Retrieval metrics** (averaged over answerable questions; top 10 retrieved):
- **Precision@K** – share of the top K chunks that are relevant.
- **Recall@K** – share of a question's gold pages found in the top K.
- **Hit@K** – at least one relevant chunk in the top K.
- **MRR** – mean of 1/rank of the first relevant chunk (rewards ranking the right passage first).
- **Latency** – mean and p95 milliseconds per query on the local CPU.

**Language conditions.**
`en` = English question. `te` = Telugu question for dense search, English for BM25 and the reranker — the reference
English question stands in for the app's LLM translation, so this is an *upper bound* on translation quality.
`te_raw` = Telugu everywhere (no translation) — shows what happens without the English pivot.

**Relevance gate.** For every question (both languages, including unanswerable ones) the best reranker probability is
recorded; for each threshold we report the share of answerable questions that would be answered and of unanswerable
questions that would be refused.

**Hallucination detector.** Each labelled claim is verified against the chunks of its source page with the production
verifier. Positive class = hallucination (unsupported or contradicted). Reported: precision, recall, F1, accuracy,
exact 3-way verdict accuracy, confusion matrix, list of mistakes.

**Generation (RAGAS-style, computed locally).**
| Metric | Definition here | RAGAS equivalent |
|---|---|---|
| Faithfulness | share of answer claims the NLI verifier marks supported | faithfulness (LLM-judged in RAGAS) |
| Hallucination rate | share of claims unsupported or contradicted | 1 − faithfulness (stricter) |
| Answer relevance | cosine(question, answer) with multilingual-E5 | answer_relevancy (RAGAS generates questions from the answer) |
| Answer similarity | cosine(answer, reference answer) | answer_similarity |
| Context recall | a gold page is among the passages given to the LLM | context_recall (page-level) |
| Abstention | unanswerable questions answered with "insufficient information" | – |

Why not the `ragas` package directly: it needs an extra judge-LLM call per metric (free-tier quota), results vary
between runs, and its API changes frequently. These local metrics are deterministic and free; the definitions follow
RAGAS so they can be cross-checked with it later.

## Limitations — read before quoting numbers
- **Small, synthetic, clean corpus.** 15 born-digital pages written for evaluation. Several configurations hit the
  ceiling (MRR 1.0); real, messy PDFs will score lower. Use the results to **compare configurations**, not as absolute
  quality claims.
- **Telugu questions were translated by the developer** and should be reviewed by a native speaker.
- `te` uses the gold English question as the "translation" (upper bound).
- Page-level relevance treats every chunk on a gold page as relevant, which inflates precision slightly for pages
  that cover several topics.
- 31 labelled claims are enough to find failure modes, not to give tight confidence intervals.
- Latency is measured on a laptop CPU and varies with background load.

To extend: add PDFs to `datasets/corpus/` (or new documents to `corpus.yaml`), add questions with gold pages to
`qa.jsonl`, and re-run.
