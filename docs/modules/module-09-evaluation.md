# Module 9 – Research and Model Evaluation

## Objective
Measure — not guess — how well DocuMind retrieves evidence, works across English and Telugu, refuses unanswerable
questions, and detects hallucinations; compare embedding models, chunking strategies and retrieval configurations;
and state the limitations honestly.

Full methodology and how to run: [`evaluation/README.md`](../../evaluation/README.md).
Results: the **Evaluation** page in the app, and `evaluation/results/<run>/summary.md` (with PNG charts).

## Concepts

### Why evaluate a RAG system in parts?
An end-to-end score ("the answer was good") does not tell you what to fix. RAG fails in distinct places, each with its own metric:

| Stage | Question | Metrics |
|---|---|---|
| Retrieval | Did we find the passage that contains the answer? | Precision@K, Recall@K, Hit@K, MRR, latency |
| Gate | Do we refuse when nothing relevant exists? | answered rate (answerable), refusal rate (unanswerable) |
| Generation | Is the answer supported, relevant, correct? | faithfulness, hallucination rate, answer relevance, answer similarity, context recall |
| Verifier | Does the hallucination detector itself work? | precision, recall, F1, confusion matrix |

### Retrieval metrics, worked example
Gold pages = {A p2, A p3}. Retrieved top 5 = [B p1, **A p2**, **A p2**, C p4, **A p3**].
- Precision@3 = 2/3 (two of the first three are relevant)
- Recall@3 = 1/2 (only A p2 of the two gold pages is in the first three); Recall@5 = 1
- MRR contribution = 1/2 (first relevant result at rank 2)

**Precision vs recall:** precision asks "how much of what I retrieved is useful?" (noise in the prompt); recall asks
"did I retrieve everything needed?" (missing evidence → wrong or refused answers). For RAG, recall@K for the K passages
given to the LLM matters most; MRR tells you whether the best passage is ranked first.

### Ground truth at page level
Questions are labelled with the **pages** that answer them, not with chunk ids, so the same labels are valid for every
chunking strategy and size. Trade-off: every chunk from a gold page counts as relevant, which inflates precision when
chunks are small (more chunks per page) — see the chunking results.

### Experimental design
One factor is varied at a time while the others are fixed (default: multilingual-E5-base, recursive 300-token chunks,
hybrid retrieval). Every question is asked in English and in Telugu. Telugu is evaluated twice: with English used for
BM25/reranking (`te`, the app's design) and with no translation at all (`te_raw`).

## Results (benchmark: 5 documents, 15 pages, 35 answerable + 6 unanswerable questions × 2 languages)

### 1. Embedding models – dense retrieval, MRR

| Model | Multilingual | English | Telugu |
|---|---|---|---|
| all-MiniLM-L6-v2 | no | 0.957 | **0.265** |
| multilingual-E5-small | yes | 0.971 | **0.854** |
| multilingual-E5-base (default) | yes | 0.971 | 0.801 |

- An English-only model is useless for Telugu questions (MRR 0.27, Recall@5 0.44); both multilingual models work
  across languages (Recall@5 0.97).
- **E5-small beat E5-base on Telugu** on this benchmark, while being ~2.5× smaller. With 35 questions the gap is a few
  questions, so it is a reason to evaluate E5-small on real data, not proof that it is better. Bigger is not
  automatically better — measuring is the only way to know.

### 2. Chunking strategy × chunk size – hybrid retrieval, English

| Chunk size | fixed MRR | recursive MRR | sentence MRR | Precision@3 (recursive) |
|---|---|---|---|---|
| 64 tokens | 0.952 | 0.971 | 0.971 | 0.724 |
| 128 tokens | 0.952 | 0.957 | 0.957 | 0.648 |
| 300 tokens | 0.971 | **0.986** | **0.986** | 0.476 |

- Sentence-aware strategies (recursive, LlamaIndex sentence) are at least as good as fixed windows at every size.
- 300 tokens gave the best MRR. Precision@3 *rises* for small chunks, but that is partly the page-level labelling
  effect (a small-chunked gold page fills the top 3 with chunks of the same page) — small chunks also give the LLM
  less context per passage.
- Recursive and sentence chunking produced identical results here because the corpus paragraphs are clean; they
  differ more on messy real documents.

### 3. Retrieval modes and reranking – MRR (multilingual-E5-base)

See the Evaluation page for the full table. Key findings from the run:
- **Hybrid > dense or keyword alone** without reranking (English 0.986).
- **Cross-encoder reranking lifts every mode to the top** (MRR 1.000 for English and translated Telugu) — the biggest
  single improvement — at a latency cost of a few seconds on CPU for 20 candidates.
- **Translation is essential for BM25 and the reranker:** Telugu with no translation drops to ~0.15 (keyword) and
  ~0.37 (reranked), because both components only understand English. This justifies the English-pivot design.

### 4. Relevance gate

At thresholds from 0.01 to 0.05 on the best reranker probability, **100% of answerable questions are answered and 100%
of unanswerable ones refused** (every unanswerable question, including near-domain distractors such as "How many
parameters does GPT-3 have?", scored below 0.01). Higher thresholds start refusing answerable questions (0.15 → 97%,
0.9 → 89%). The default `RELEVANCE_THRESHOLD` was therefore changed from 0.15 to **0.05** — an evidence-based decision.

### 5. Hallucination detector (31 labelled claims)

| Metric | Value |
|---|---|
| Precision (flagged claims that were hallucinations) | **0.94** |
| Recall (hallucinations caught) | **1.00** |
| F1 | 0.97 |
| Exact verdict accuracy (supported / unsupported / contradicted) | 0.90 |

Mistakes, and what they teach:
- *"Mawsynram receives more rain than Mumbai."* — true according to a table, but flagged **unsupported**: NLI cannot
  compare two table rows. Comparisons and arithmetic are a known blind spot.
- *"The big Transformer reached 31.2 BLEU"* — correctly flagged, but as unsupported rather than contradicted.
- *"Marie Antoinette was executed in October 1793"* — flagged as contradicted rather than unsupported (the page
  mentions Louis XVI's execution in January 1793). Still correctly flagged as a hallucination.

### 6. End-to-end answers (needs a Gemini key)
`run_generation_eval.py` measures faithfulness, hallucination rate, answer relevance, answer similarity, context recall,
abstention and latency for English and Telugu. Run it after adding `GEMINI_API_KEY`:
```powershell
backend\.venv\Scripts\python evaluation\run_generation_eval.py --limit 20 --languages en te
```

## Limitations
- Small, clean, synthetic corpus → ceiling effects (several configurations reach MRR 1.0). Use these results to
  **compare** configurations; expect lower absolute numbers on real, messy PDFs.
- Telugu questions were translated by the developer; a native speaker should review them.
- `te` uses the reference English question as the translation (upper bound for the LLM translation step).
- 31 claims reveal failure modes but give wide confidence intervals.
- Latency was measured on a laptop CPU.
- RAGAS-style metrics are computed locally (deterministic, free) rather than with the `ragas` package; see the evaluation README.

## Interview questions
1. Define Precision@K, Recall@K and MRR. Which matters most for RAG and why?
2. Why label relevance at page level? What bias does that introduce?
3. Why did an English-only embedding model fail on Telugu questions?
4. Your smaller model beat the larger one on Telugu — how would you decide which to deploy?
5. How did you choose the relevance threshold?
6. How do you evaluate a hallucination detector? What are its blind spots?
7. What is faithfulness vs answer relevance vs answer correctness?
8. What are the limitations of your benchmark, and how would you build a better one?
