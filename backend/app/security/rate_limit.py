# Author: Pradeep Sahoo — Retail Nexus AI
"""Simple in-memory rate limiter keyed by client+route. Good enough for a single-node dev build."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class SlidingWindowLimiter:
    def __init__(self, window_seconds: int = 60) -> None:
        self.window = window_seconds
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def check(self, key: tuple[str, str], limit: int) -> None:
        now = time.monotonic()
        q = self._hits[key]
        cutoff = now - self.window
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded ({limit}/minute)",
            )
        q.append(now)


_LIMITER = SlidingWindowLimiter(window_seconds=60)


def rate_limited(limit_per_minute: int):
    def _dep(request: Request) -> None:
        client = request.client.host if request.client else "unknown"
        _LIMITER.check((client, request.url.path), limit_per_minute)
    return _dep
