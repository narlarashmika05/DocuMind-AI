# Module 2 – Authentication and Document Management

## Objective
Registration, login/logout, profiles, and multi-PDF upload/list/view/delete — with each user able to see only their own documents.

## Concepts
| Concept | Explanation |
|---|---|
| Password hashing (Argon2id) | Store a slow, memory-hard one-way hash, never the password. Brute-forcing a leaked hash is impractical. `pwdlib` is used because `passlib` is unmaintained. |
| JWT access token | Signed token `{sub: user_id, type: access, exp}` valid 15 min. The server verifies the signature (algorithm fixed to HS256, so `alg=none` attacks fail). |
| Refresh token | Random 64-char string in an **httpOnly, SameSite=Lax** cookie scoped to `/api/v1/auth`, valid 7 days. Only its SHA-256 is stored. |
| Rotation + reuse detection | Every refresh issues a new token and revokes the old one. If a revoked token is used again (after a 10 s grace period for parallel tabs), it was likely stolen → all sessions revoked. |
| Token storage in the browser | Access token in memory (not localStorage → not readable by injected scripts); refresh cookie not readable by JavaScript at all. After a reload, `AuthProvider` silently calls `/auth/refresh`. |
| Timing-attack-safe login | Unknown emails are checked against a dummy hash, so response time doesn't reveal which emails exist. Same error message for wrong email or password. |
| Alembic migrations | Version-controlled schema changes with upgrade **and** downgrade. (MySQL lesson learnt: drop tables, not FK-backed indexes, in downgrades; give new NOT NULL columns a server default.) |
| IDOR protection | Every document query includes `user_id = current user` in SQL. Other users' documents → **404**, not 403 (no existence leak). |
| Upload validation | Extension + `%PDF-` magic bytes; size measured while streaming (1 MB chunks, client size not trusted); SHA-256 duplicate detection; random UUID file names in per-user folders; filenames sanitised (`../../x.pdf` → `x.pdf`). Module 11 adds active-content scanning. |

## Endpoints
`POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET/PATCH /users/me`, `POST /users/me/password`, `POST /documents`, `GET /documents`, `GET/DELETE /documents/{id}`, `GET /documents/{id}/file` — see `docs/api.md`.

## Frontend
`AuthProvider` (state + silent refresh), Axios interceptors (attach token; on 401 refresh once and retry; shared refresh promise because each refresh token is single-use), `ProtectedRoute`/`GuestRoute` (redirect back to the requested page after login), Login/Register/Dashboard/Documents/Profile pages, drag-and-drop upload with progress.

## Tests
`tests/test_auth.py` (registration rules, login, token rotation, reuse detection, logout, profile, password change) and `tests/test_documents.py` (upload rules, duplicates, size limit, path traversal, isolation between users) — run with an in-memory SQLite database and temporary storage.

## Interview questions
1. Hashing vs encryption for passwords; why Argon2 rather than SHA-256?
2. What is inside a JWT and why can't a user modify it?
3. Why both short-lived access tokens and long-lived refresh tokens?
4. localStorage vs httpOnly cookie for tokens?
5. How does refresh-token reuse detection catch theft?
6. What is IDOR and how is it prevented here? Why 404 instead of 403?
7. Why isn't the file extension enough to validate an upload?
8. What is a timing attack on login?
9. What is CSRF and how does `SameSite=Lax` help?
10. Why database migrations instead of `create_all()`?
