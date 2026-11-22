"""HTTP-level protections that apply to every request."""

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger("documind.http")

API_CSP = "default-src 'none'; frame-ancestors 'none'"
DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


def max_body_bytes() -> int:
    # Largest legitimate request: a full batch of maximum-size PDFs, plus 1 MB for form overhead.
    return (settings.MAX_UPLOAD_SIZE_MB * settings.MAX_FILES_PER_UPLOAD + 1) * 1024 * 1024


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        request.state.request_id = request_id

        # Reject oversized bodies before reading them (the client cannot make us buffer gigabytes).
        max_body = max_body_bytes()
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > max_body:
            return JSONResponse({"detail": "Request body is too large."}, status_code=413, headers={"X-Request-ID": request_id})

        try:
            response = await call_next(request)
        except Exception:
            # Log the full error with its id; the client gets no internal details.
            logger.exception("Unhandled error (request %s %s %s)", request_id, request.method, request.url.path)
            response = JSONResponse(
                {"detail": "An internal error occurred. Please try again.", "request_id": request_id}, status_code=500
            )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers.setdefault("Cache-Control", "no-store")
        if not request.url.path.startswith(DOCS_PATHS):  # Swagger UI needs its own scripts
            response.headers.setdefault("Content-Security-Policy", API_CSP)
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
