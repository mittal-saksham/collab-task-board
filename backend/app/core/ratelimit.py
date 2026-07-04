"""A small in-memory rate limiter, used as a FastAPI dependency.

Why hand-rolled instead of a library: the needs are tiny (three endpoints), the
algorithm is worth being able to explain (sliding window over a deque of
timestamps), and an extra dependency isn't. The trade-off matches the WS
manager's: state is in-memory and per-process, which is exactly right for the
single-instance deploy this app targets — multi-instance would move this to
Redis alongside the WS pub/sub.

Usage:
    limiter = RateLimiter(limit=10, window_seconds=60)

    @router.post("/login", dependencies=[Depends(limiter)])
    def login(...): ...

Keyed by client IP. Over the limit → 429 with a Retry-After header.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

# Every limiter registers itself here so tests can wipe state between cases
# (the same way the DB is truncated after each test).
_ALL_LIMITERS: list["RateLimiter"] = []


def reset_all() -> None:
    """Clear every limiter's state. For tests only."""
    for limiter in _ALL_LIMITERS:
        limiter.reset()


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window = window_seconds
        # ip -> timestamps of that ip's recent requests (oldest first).
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        # FastAPI can serve requests concurrently; the deque ops must not race.
        self._lock = threading.Lock()
        _ALL_LIMITERS.append(self)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def __call__(self, request: Request) -> None:
        # request.client is None in some ASGI test setups; treat that as one
        # shared client rather than skipping the limit.
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with self._lock:
            hits = self._hits[ip]
            # Slide the window: drop hits older than `window` seconds.
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                retry_after = int(self.window - (now - hits[0])) + 1
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests — slow down.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)


# The shared instances. Login/signup limits blunt credential stuffing and
# signup abuse (each attempt also costs ~100ms of bcrypt CPU — see docs/13);
# summarize guards the Anthropic API budget.
login_limiter = RateLimiter(limit=10, window_seconds=60)
signup_limiter = RateLimiter(limit=10, window_seconds=60)
summarize_limiter = RateLimiter(limit=5, window_seconds=60)
