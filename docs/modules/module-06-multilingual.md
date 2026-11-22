# Module 6 – Multilingual NLP (English and Telugu)

## Objective
Users can ask in **English or Telugu** about **English documents** and receive answers in the language they choose, with the same citations and verification.

## Language combinations supported

| Question | Documents | Answer | How |
|---|---|---|---|
| English | English | English | standard pipeline |
| Telugu | English | Telugu | dense search with the Telugu question (cross-lingual embeddings); BM25 + reranker with the English translation; answer generated in English, translated in the same LLM call |
| Telugu | English | English | `answer_language = en` |
| English | English | Telugu | `answer_language = te` |
| Telugu | Telugu (typed/OCR'd) | either | multilingual embeddings + Telugu OCR (`OCR_LANGUAGES=eng+tel`) |

## Concepts

### NLP and Transformers in brief
- **Tokenisation:** text → sub-word tokens. Multilingual models use a shared vocabulary (SentencePiece) covering many scripts; Telugu words split into more tokens than English ones.
- **Transformer encoder:** each token's vector is updated by **self-attention** — every token looks at every other token and mixes in relevant information. Stacking layers builds contextual meaning ("bank" near "river" vs "loan").
- **Multilingual pre-training:** XLM-RoBERTa (the base of multilingual-E5) was trained on text in ~100 languages. Because concepts co-occur similarly across languages, similar meanings end up near each other regardless of language.
- **Contrastive fine-tuning:** E5 was then trained on (question, relevant passage) pairs to pull matches together and push non-matches apart — including translation pairs, giving a **shared cross-lingual space**: a Telugu question lands next to the English passage that answers it.

### Language detection
Telugu has its own Unicode block (U+0C00–U+0C7F). If ≥30% of a question's letters are Telugu → `te`. Deterministic, instant, and more reliable on short questions than statistical language-ID models. Mixed questions ("BERT model ఎలా పని చేస్తుంది?") count as Telugu.

### Why translate at all if embeddings are cross-lingual?
- **BM25** matches words — Telugu words never occur in English documents.
- The **reranker** (ms-marco MiniLM) is English-only.
- **NLI verification** (DeBERTa) is English-only.
So the pipeline keeps **one canonical English version** of the question and the answer, and uses Telugu only at the edges (input understanding + output display). Verification always runs on the English claims, then the verified claims are shown in Telugu.

### Generating the Telugu answer
The answer prompt asks Gemini for English claims **and** `translated_claims` (same order) in a single call — no extra request. Technical terms, numbers and names may stay in English, which is how Telugu speakers write about technical topics. If the translation is missing, the English claim is shown with a warning.

## Measured result (real models, Module 4 check)

| Model | English → English top-1 | Telugu → English top-1 |
|---|---|---|
| all-MiniLM-L6-v2 (English-only) | 5/5 | 1/5 (chance level) |
| multilingual-e5-base | 5/5 | 5/5 |

The full, larger comparison (Precision@K, Recall@K, MRR, three models, English vs Telugu) is produced by the evaluation framework in Module 9.

## Files
| File | Purpose |
|---|---|
| `app/services/multilingual/language.py` | Script-based language detection, answer-language resolution |
| `app/services/llm/prompts.py` | Query rewriting/translation prompt; `translated_claims` rule |
| `app/services/rag/pipeline.py` | Uses the original question for dense search, English for BM25/rerank/NLI |
| `frontend/src/components/chat/Composer.jsx` | Answer language selector |
| `frontend/src/pages/ProfilePage.jsx` | Preferred language (default for the chat selector) |
| `evaluation/datasets/qa.jsonl` | Questions in English **and** Telugu (Module 9) |

## Test
```powershell
pytest tests/test_chat.py -k "telugu or language" -v
```
In the UI: Profile → preferred language **తెలుగు** → Chat → ask `ఈ పత్రంలోని ముఖ్యమైన ఫలితాలు ఏమిటి?` → the answer appears in Telugu; the meta line shows the English question used for search.

## Limitations (be honest about these in interviews)
- Telugu answers are machine translations; check important wording against the English evidence.
- Verification is done on English claims; a translation error after verification would not be caught.
- Romanised Telugu ("ee paper lo results enti?") is detected as English; the LLM rewrite step usually still understands it, but retrieval quality is lower.
- Telugu OCR quality on scanned pages is noticeably lower than English OCR.

## Interview questions
1. How can a Telugu question retrieve an English passage? Explain the shared embedding space.
2. What is self-attention, and why do Transformers handle context better than RNNs?
3. Why still translate the question if the embeddings are multilingual?
4. How do you detect the language of a short question?
5. What is subword tokenisation and why does it matter for Telugu?
6. How would you evaluate multilingual retrieval quality? (Module 9: same questions in both languages, compare P@K/R@K/MRR)
7. What risks does machine translation add to a hallucination-aware system?
