# Module 12 – Deployment and Documentation

## Objective
Ship the whole system reproducibly (one command), explain cloud options, and document it for users, reviewers and interviewers.

## Containers
| File | What it does |
|---|---|
| `backend/Dockerfile` | Python 3.11 slim + Tesseract (eng, tel); **CPU-only PyTorch** first (avoids ~2.5 GB of CUDA libraries), then requirements; non-root user; health check; runs `alembic upgrade head` then Uvicorn |
| `frontend/Dockerfile` | Multi-stage: Node builds the static app → nginx serves it (no Node or source code in the final image) |
| `frontend/nginx.conf` | Serves the SPA (`try_files` → `index.html`), proxies `/api` to the backend (same origin: no CORS, cookies work), 260 MB upload limit, long timeout for answers, security headers, immutable caching for hashed assets |
| `docker-compose.yml` | `db` (MySQL 8.4, utf8mb4, health check, no public port) → `backend` (waits for healthy DB; volumes for storage and model cache) → `frontend` on port 8080 |
| `.env.docker.example` | Secrets for compose (`MYSQL_*`, `JWT_SECRET_KEY`, `GEMINI_API_KEY`) — copy to `.env` |
| `*.dockerignore` | Keep venvs, node_modules, local `.env` and user data out of images |

```powershell
Copy-Item .env.docker.example .env   # edit secrets
docker compose up --build            # http://localhost:8080
```

## Concepts
- **Image vs container:** an image is a read-only template (OS + dependencies + code); a container is a running instance.
- **Layers and caching:** dependency installation is placed before `COPY app` so code changes don't reinstall PyTorch.
- **Multi-stage builds:** build tools stay in the build stage; the runtime image is small.
- **Volumes:** data (MySQL, uploads, vectors, model cache) outlives containers.
- **Health checks and `depends_on: service_healthy`:** start order based on readiness, not just process start.
- **Reverse proxy:** one public entry point that serves static files and forwards API calls.

## Cloud
See `docs/deployment.md` for the AWS mapping (EC2 + RDS MySQL + S3 + Parameter Store + ALB/ACM + ECR + CloudWatch), a production checklist, and free-hosting notes.

## Documentation map
| Document | Audience |
|---|---|
| `README.md` | Everyone: what, why, results, how to run |
| `docs/architecture.md` | Engineers: diagrams, data model, design decisions, scaling |
| `docs/api.md` + `/docs` (Swagger) | API users |
| `docs/deployment.md` | Operators |
| `docs/demo-guide.md` | Presenting the project |
| `docs/modules/*.md` | Learning: concepts, steps, errors, interview questions per module |
| `evaluation/README.md` | Reproducing the benchmark |

## Status
The Docker files were written and reviewed but **not built on the development machine** (Docker was not installed). Build once with `docker compose up --build` and fix anything environment-specific.

## Interview questions
1. Why containerise? What problem does Docker Compose solve?
2. How did you keep the backend image small and builds fast?
3. Why put nginx in front of the app?
4. How are secrets provided in Docker and in AWS?
5. How would you deploy this on AWS within a small budget?
6. What would change to run several backend instances?
