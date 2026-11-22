"""Simple sliding-window rate limiting.

Protects login from password guessing, registration from mass sign-ups and the LLM
endpoint from exhausting the API quota. State lives in this process's memory, which
is fine for a single server; with several servers the counters must be shared
(e.g. Redis) - see docs/modules/module-11-testing-security.md.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, status

from app.core.config import settings


class RateLimiter:
    def __init__(self, name: str, limit: int, window_seconds: int):
        self.name = name
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """Record one request for `key`; raise 429 if the limit is exceeded."""
        if not settings.RATE_LIMIT_ENABLED:
            return
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - self.window:  # forget requests outside the window
                hits.popleft()
            if len(hits) >= self.limit:
                retry_after = int(hits[0] + self.window - now) + 1
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    f"Too many requests. Please try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


login_limiter = RateLimiter("login", limit=10, window_seconds=60)
register_limiter = RateLimiter("register", limit=5, window_seconds=3600)
ask_limiter = RateLimiter("ask", limit=20, window_seconds=60)
upload_limiter = RateLimiter("upload", limit=30, window_seconds=3600)
search_limiter = RateLimiter("search", limit=60, window_seconds=60)

ALL_LIMITERS = [login_limiter, register_limiter, ask_limiter, upload_limiter, search_limiter]
