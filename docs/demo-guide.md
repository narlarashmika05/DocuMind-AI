# Demo guide (10 minutes)

A script for showing DocuMind AI in an interview or presentation. Prepare once:
start the backend and frontend, register a demo account, and upload the five evaluation PDFs from
`evaluation/datasets/corpus/` plus one real paper (e.g. "Attention Is All You Need" from arXiv). Wait until all are **Ready**.

## 1. The problem (30 s)
"LLMs answer confidently even when they are wrong, they can't see your private documents, and most tools only work in English. DocuMind answers from your documents, cites the exact page, checks every sentence against the evidence, and works in English and Telugu."

## 2. Documents (1.5 min)
- **Documents** page: upload a PDF → show the live progress stages (extracting → describing figures → chunking → embedding).
- Try uploading a `.txt` renamed to `.pdf` → rejected by the signature check (security).
- Open a document in the **viewer**: page image next to extracted text; show a detected **table** rendered from Markdown and a **figure** with its AI-generated description.
- Mention: two-column reading order, header/footer removal, OCR for scanned pages.

## 3. Grounded answers (2 min)
- **Chat**: "What BLEU score did the big Transformer achieve on English-to-German?"
- Click the citation chip **[1]** → source panel shows the passage, the table, and the original page image.
- Point at the **evidence check**: every statement has a verdict and confidence.

## 4. Honesty (1 min)
- Ask "Who won the 2011 Cricket World Cup?" → **"I could not find enough information"** — the relevance gate refused without even calling the LLM.

## 5. Telugu (1.5 min)
- Profile → preferred language **తెలుగు**, or pick it in the chat composer.
- Ask "ట్రాన్స్‌ఫార్మర్ ఎన్ని అటెన్షన్ హెడ్‌లను ఉపయోగిస్తుంది?" → the answer appears in Telugu with the same citations; the meta line shows the English question used for search.
- Explain the English pivot: cross-lingual embeddings for retrieval; BM25, reranker and verifier on English.

## 6. Under the hood (1.5 min)
- **Search** page: same question in Semantic vs Keyword vs Hybrid, with and without reranking — show how ranking changes.
- **Evaluation** page: Telugu → English retrieval with the multilingual model vs the English-only baseline; hybrid + rerank is best; the relevance-gate trade-off chart; hallucination detector precision/recall with its confusion matrix and the mistakes it makes.

## 7. Engineering (1 min)
- Security: Argon2, JWT + rotating httpOnly refresh cookie with reuse detection, per-user isolation (404 for others' documents), rate limits, PDF active-content scanning, prompt-injection fencing.
- Testing: ~100 backend tests (fake models → fast, offline) + frontend unit tests; evaluation with real models.
- Deployment: Docker Compose (nginx + FastAPI + MySQL); AWS mapping.

## 8. Limitations (30 s) — say them before you're asked
- Verification is a signal, not proof (e.g. it misses comparisons across table rows).
- Telugu answers are machine translations; the benchmark is small and synthetic.
- CPU-only: first questions are slow while models load.

## Reproduce the measured numbers
```powershell
backend\.venv\Scripts\python evaluation\build_corpus.py
backend\.venv\Scripts\python evaluation\run_retrieval_eval.py
backend\.venv\Scripts\python evaluation\run_verifier_eval.py
backend\.venv\Scripts\python evaluation\run_generation_eval.py --limit 20   # needs GEMINI_API_KEY
```
