# Module 1 – Project Setup and Architecture

## Objective
A React page that calls a FastAPI endpoint, which checks MySQL — with configuration in environment files and code in Git.

## Concepts
| Concept | Explanation |
|---|---|
| Client–server, REST | The browser sends HTTP requests (`GET /api/v1/health`); the server answers with JSON. Resources have URLs, HTTP verbs say what to do. |
| ASGI / Uvicorn | FastAPI is the application; Uvicorn is the server process listening on port 8000 and passing requests to it. |
| CORS | Browsers block a page on `:5173` from reading responses from `:8000` unless the API allows that origin. Only listed origins are allowed. CORS protects users' browsers, **not** the API (curl ignores it). |
| Environment variables | Configuration and secrets live outside the code (12-factor app): same code on laptop, Docker and cloud; secrets never in Git. |
| ORM + connection pool | SQLAlchemy maps Python objects to SQL. A pool reuses connections; `pool_pre_ping` discards ones MySQL closed. |
| Dependency injection | `Depends(get_db)` gives each request a session and always closes it; tests swap in a fake. |
| Pydantic | Validates request/response shapes; `HealthResponse` guarantees what the frontend receives. |
| utf8mb4 | MySQL's real UTF-8 (the old `utf8` is 3-byte and can corrupt text). Needed for Telugu. |
| SPA routing | React Router changes pages in the browser without reloading. |
| Health checks | 200 when healthy, **503** when the database is down, so Docker/load balancers can react to the status code. |

## Request flow
```
React (5173) → Axios GET /api/v1/health → CORS check → health_check() ← Depends(get_db)
 → SELECT 1 on MySQL → HealthResponse JSON (200 or 503) → React state → green/amber/red card
```

## Key files
`backend/app/main.py`, `backend/app/core/config.py`, `backend/app/db/session.py`, `backend/app/api/v1/routes/health.py`, `backend/tests/test_health.py`, `frontend/src/api/client.js`, `frontend/src/components/BackendStatus.jsx`.

## Setup (Windows)
1. Python 3.11.9: https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe ("Add to PATH" unchecked; use `py -3.11`).
2. MySQL (8.4 LTS or 9.x). Create the database and a least-privilege user:
   ```sql
   CREATE DATABASE documind CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
   CREATE USER 'documind_user'@'localhost' IDENTIFIED BY 'your-password';
   GRANT ALL PRIVILEGES ON documind.* TO 'documind_user'@'localhost';
   ```
3. Backend: `cd backend; py -3.11 -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt; Copy-Item .env.example .env` (edit it), `pytest`, `uvicorn app.main:app --reload`.
4. Frontend: `cd frontend; npm install; Copy-Item .env.example .env; npm run dev` → http://localhost:5173.

## Common errors
| Error | Fix |
|---|---|
| `Activate.ps1 cannot be loaded` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `No module named 'app'` | run commands inside `backend/` |
| `(1045) Access denied` | wrong `MYSQL_PASSWORD` in `.env`, or file not saved |
| `(2003) Can't connect` | MySQL service stopped (`Start-Service MySQL97`) |
| CORS error in console | open the URL exactly as listed in `CORS_ORIGINS` (`localhost` vs `127.0.0.1`) |

## Interview questions
1. What is CORS and why doesn't it secure an API?
2. Why configuration in environment variables?
3. What does a connection pool do; why `pool_pre_ping`?
4. `def` vs `async def` endpoints with a synchronous ORM?
5. How does dependency injection make testing easier?
6. Why should a health check return 503 when the database is down?
7. `utf8` vs `utf8mb4` in MySQL?
8. Why is a `VITE_` variable never safe for secrets?
