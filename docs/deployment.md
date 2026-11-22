# Deployment

## Option A – Docker Compose (one command, any machine with Docker)

```
browser ──► frontend (nginx :8080) ──/api──► backend (FastAPI :8000) ──► db (MySQL, internal only)
                 static React build            models + storage volumes
```

1. Install **Docker Desktop** (Windows/macOS) or Docker Engine (Linux). On Windows give Docker at least 6 GB RAM (Settings → Resources).
2. In the project root:
   ```powershell
   Copy-Item .env.docker.example .env      # then edit: passwords, JWT secret, optional Gemini key
   docker compose up --build
   ```
3. Open **http://localhost:8080**. The first start downloads ~2 GB of models into the `models` volume; later starts are fast.
4. Useful commands:
   ```powershell
   docker compose logs -f backend      # watch processing / errors
   docker compose down                 # stop (data kept in volumes)
   docker compose down -v              # stop AND delete all data
   ```

Why these choices:
- **nginx serves the React build and proxies `/api`** → one origin: no CORS problems, the refresh cookie works, the API is not exposed separately.
- **MySQL has no published port** → reachable only by the backend container.
- **CPU-only PyTorch** in the image avoids ~2.5 GB of CUDA libraries.
- **Non-root user** in the backend container; **migrations run on start** (`alembic upgrade head`).
- The compose file uses **MySQL 8.4 LTS** (long-term support, the safest server choice); the app is also tested on MySQL 9.7 locally.

> The Docker setup was written for this project but could not be built on the development machine (Docker was not installed). Run `docker compose up --build` once and report any error output.

## Option B – AWS (fundamentals)

| Need | AWS service | Free-tier / low-cost notes |
|---|---|---|
| Run the containers | **EC2** (t3.large or larger: models need ~4 GB RAM) with Docker Compose — simplest | t2/t3.micro (1 GB) is too small for the ML models |
| Managed database | **RDS for MySQL** | Free tier: db.t3.micro, 20 GB for 12 months |
| File storage | **S3** for PDFs and figures (swap the local storage service for boto3 + presigned URLs) | 5 GB free for 12 months |
| Secrets | **SSM Parameter Store** (SecureString) or Secrets Manager → injected as environment variables | Parameter Store standard tier is free |
| HTTPS + domain | **Application Load Balancer + ACM certificate**, or Caddy/nginx with Let's Encrypt on the EC2 instance | ACM certificates are free |
| Container images | **ECR** | 500 MB/month free for 12 months |
| Logs/metrics | **CloudWatch** | basic metrics free |

Minimal production checklist:
- `ENVIRONMENT=production` (secure cookies, HSTS), long random `JWT_SECRET_KEY`, real `CORS_ORIGINS`/`PUBLIC_URL`.
- HTTPS everywhere; security group allows only 80/443 publicly, MySQL only from the app.
- Back up the MySQL database and the storage volume (or S3 bucket versioning).
- Run several backend replicas only after moving rate-limit counters and background jobs to Redis (see architecture.md → scaling notes).

## Option C – Free hosting for demos
- **Frontend:** the static `frontend/dist` build on Netlify/Vercel/Cloudflare Pages (set `VITE_API_URL` to the public API URL; the backend `CORS_ORIGINS` must include the frontend URL, and cookies then need `SameSite=None; Secure` — prefer Option A's same-origin setup).
- **Backend:** needs ~4 GB RAM for the models, which most free tiers do not offer; for a demo, run it locally and share a screen recording instead.

## Environment variables (backend)

See `backend/.env.example` for the full, commented list. Required: `MYSQL_*`, `JWT_SECRET_KEY`. Optional: `GEMINI_API_KEY` (answers, Telugu translation, figure descriptions), model and threshold settings.
