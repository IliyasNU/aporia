"""Simple in-memory rate limiting (SEC-03): N requests per key per time window.

Keys look like "login:ip:203.0.113.7" or "comment:user:<uuid>". The counters live
in this process's memory, which is right for Aporia's single API process. If you
ever run several API processes, each one counts separately (limits multiply by
the number of processes); move the counters to PostgreSQL then.
"""

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import AppError


@dataclass(frozen=True)
class Limit:
    name: str
    max_requests: int
    window_seconds: int


# One place to see and tune every limit.
REGISTER = Limit("register", max_requests=10, window_seconds=3600)
LOGIN_PER_IP = Limit("login-ip", max_requests=20, window_seconds=300)
LOGIN_PER_EMAIL = Limit("login-email", max_requests=10, window_seconds=300)
SUBSCRIBE = Limit("subscribe", max_requests=10, window_seconds=3600)
COMMENT = Limit("comment", max_requests=20, window_seconds=600)
REPORT = Limit("report", max_requests=20, window_seconds=3600)


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()  # sync endpoints run in a thread pool

    def hit(self, limit: Limit, subject: str) -> None:
        """Count one request; raise 429 if the limit for this subject is used up."""
        if not get_settings().rate_limits_enabled:
            return
        key = f"{limit.name}:{subject}"
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - limit.window_seconds:
                hits.popleft()
            if len(hits) >= limit.max_requests:
                retry_after = int(hits[0] + limit.window_seconds - now) + 1
                raise AppError(
                    429,
                    "rate_limited",
                    "Too many attempts. Please wait a little and try again.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)
            if len(self._hits) > 10_000:
                self._forget_idle(now)

    def _forget_idle(self, now: float) -> None:
        """Drop counters with no hit in the last hour, so memory stays bounded."""
        for key in [k for k, hits in self._hits.items() if not hits or hits[-1] < now - 3600]:
            del self._hits[key]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    """The visitor's IP. Behind nginx, uvicorn's --proxy-headers puts the real one here."""
    return request.client.host if request.client else "unknown"
