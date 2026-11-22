# Module 11 – Testing and Security

## Test strategy

| Layer | Tool | What | Count |
|---|---|---|---|
| Unit (backend) | pytest | chunking strategies, reading order, header removal, table Markdown, deskew, metrics, injection guard | ~35 |
| API (backend) | pytest + FastAPI TestClient | every endpoint: auth flows, uploads, processing, search, chat, evaluation, errors | ~60 |
| Integration | pytest with real PDFs generated in code | upload → background processing → pages/elements/chunks → search → RAG → verification → stored claims | in API tests |
| Security | pytest | rate limits, headers, oversized bodies, error leakage, malicious PDFs, account deletion, isolation, committed-secret scan | 13 |
| Frontend unit | Vitest | validation, formatting, status and verification helpers | 6 |
| Model quality | evaluation framework (Module 9) | real embedding/reranker/NLI models on a labelled benchmark | – |
| Manual smoke | scripts against real MySQL + real models | MySQL types (MEDIUMTEXT/JSON), migrations up/down/up, cross-lingual retrieval, NLI | – |

**Why fakes in tests?** Real models need GBs of downloads and seconds per call; Gemini needs a key, network and quota. Tests replace them (`tests/fakes.py`: hashed bag-of-words embedder, word-overlap reranker/NLI, scripted LLM) so ~100 tests run offline in about 3 minutes and are deterministic. The real models are measured separately by the evaluation framework — the right tool for quality, while tests check behaviour and wiring.

**Test database:** in-memory SQLite (`StaticPool`, foreign keys switched on) and a temporary storage folder per test; background jobs are pointed at the same database through the overridable `get_session_factory` dependency.

```powershell
cd backend; .\.venv\Scripts\Activate.ps1
pytest -q                         # all backend tests
pytest tests/test_security.py -v  # security tests only
cd ..\frontend; npm test
```

## Security controls (threat → defence)

| Threat | Defence | Where |
|---|---|---|
| Password theft from DB leak | Argon2id hashes; refresh tokens stored as SHA-256 | `core/security.py` |
| Password guessing | 10 logins/min per IP; same message for wrong email/password; constant-time-ish login (dummy hash) | `core/rate_limit.py`, `auth_service.py` |
| Token theft via XSS | access token only in memory; refresh token httpOnly cookie; rotation with reuse detection | `api/v1/cookies.py`, `auth_service.py` |
| CSRF | refresh cookie `SameSite=Lax`, path-scoped to `/api/v1/auth`; all other calls need a Bearer header | `cookies.py` |
| Accessing others' data (IDOR) | `user_id` in every SQL query and vector filter; 404 for others' resources; tested for every endpoint type | services, routes, `test_*` |
| Malicious uploads | extension + magic bytes; streamed size limit; 413 before reading oversized bodies; **reject PDFs with JavaScript, launch actions, embedded files, rich media, XFA**; random storage names; path checks when serving files; page limit; encrypted PDFs refused | `file_validator.py`, `document_service.py`, `middleware.py` |
| Prompt injection in documents | sources wrapped in `<source>` tags + "data, never instructions" rule; tag-like text neutralised; suspicious passages flagged to the LLM, logged and shown as a warning; invented citations dropped; answers verified | `injection_guard.py`, `prompts.py`, `rag/pipeline.py` |
| API key exposure | keys only in `backend/.env` (gitignored) or environment; frontend has only `VITE_API_URL`; test fails if a Google API key or private key is committed or a `.env` is tracked | `config.py`, `test_security.py` |
| LLM quota abuse | 20 questions/min per user; relevance gate avoids needless calls; figure-description cap and delay | `rate_limit.py`, `figures.py` |
| Information leakage in errors | global handler returns a generic message + request id; details only in server logs | `middleware.py` |
| Clickjacking, MIME sniffing | `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, strict CSP on API responses, HSTS in production | `middleware.py`, `nginx.conf` |
| Data retention | account deletion removes files, extracted images, vectors, chats | `routes/users.py` |
| Input validation | Pydantic schemas: lengths, enums, email format, password strength; question ≤ 2000 chars | `schemas/*` |

## Known limitations (and what production would add)
- Rate-limit counters are per process → use Redis when running several replicas.
- No email verification / password reset flow (needs an email provider).
- No antivirus scan of uploads (e.g. ClamAV) — active-content checks cover PDF-specific risks only.
- Prompt-injection defences reduce risk but no known method fully prevents it; the design limits the damage (the LLM has no tools, no secrets in its prompt, and its output is verified and shown with sources).
- Registration reveals whether an email exists (409) — an accepted usability trade-off; rate-limited.

## Interview questions
1. Unit vs API vs integration tests — what did you test at each level?
2. How do you test code that depends on an LLM?
3. What is prompt injection and how do you defend a RAG system against it?
4. How do you stop one user reading another's documents? How did you test it?
5. What can a malicious PDF do, and how did you defend against it?
6. Why return a generic 500 message with a request id?
7. How would you make rate limiting work across multiple servers?
8. How do you keep secrets out of Git, and how did you enforce it automatically?
