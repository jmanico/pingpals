"""Per-user rate limiting + concurrency caps (issue 024, SEC-6.1/6.3).

Default-deny baseline: every authenticated endpoint inherits a baseline per-user request-rate
limit unless it declares a stricter one — an unlisted endpoint is NEVER unbounded. Sensitive
endpoints (auth, OAuth callback, DSR, import, delivery) get tighter limits, and quota/IO-heavy
operations (import, export) additionally get a per-user concurrency cap. Exceeding any limit
returns 429 with a ``Retry-After`` and enqueues no work; the response discloses no internal config.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from flask import Flask, current_app, g, jsonify, request


@dataclass(frozen=True)
class Limit:
    """A fixed-window request-rate limit: ``max_requests`` per ``window_seconds``."""

    max_requests: int
    window_seconds: int


class FixedWindowRateLimiter:
    """In-memory fixed-window counter. (Production uses a shared store behind this interface.)"""

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or time.monotonic
        self._windows: dict[str, tuple[float, int]] = {}

    def check(self, key: str, limit: Limit) -> bool:
        """Return True if the request is allowed; False if it exceeds ``limit`` (fail closed)."""
        now = self._clock()
        start, count = self._windows.get(key, (now, 0))
        if now - start >= limit.window_seconds:
            start, count = now, 0  # new window
        count += 1
        self._windows[key] = (start, count)
        return count <= limit.max_requests


class ConcurrencyCap:
    """Per-(user, op) in-flight cap for quota/IO-heavy work (import/export)."""

    def __init__(self) -> None:
        self._active: dict[str, int] = {}

    def try_acquire(self, key: str, cap: int) -> bool:
        active = self._active.get(key, 0)
        if active >= cap:
            return False  # reject without starting provider-quota-consuming work (AC-02)
        self._active[key] = active + 1
        return True

    def release(self, key: str) -> None:
        if self._active.get(key, 0) > 0:
            self._active[key] -= 1


_EXT_KEY = "pingpals_rate_limit"


def register_rate_limiting(
    app: Flask,
    *,
    baseline: Limit | None = None,
    endpoint_limits: dict[str, Limit] | None = None,
    identity: Callable[[], str] | None = None,
    limiter: FixedWindowRateLimiter | None = None,
) -> None:
    """Install the default-deny baseline limiter and per-endpoint overrides."""
    baseline = baseline or Limit(max_requests=120, window_seconds=60)
    endpoint_limits = endpoint_limits or {}
    limiter = limiter or FixedWindowRateLimiter()
    # Identity for the rate key: authenticated user if available, else remote address (auth eps).
    identity = identity or (lambda: request.remote_addr or "anonymous")

    app.extensions[_EXT_KEY] = {
        "limiter": limiter,
        "baseline": baseline,
        "endpoint_limits": endpoint_limits,
        "concurrency": ConcurrencyCap(),
    }

    @app.before_request
    def _enforce_rate_limit():  # type: ignore[no-untyped-def]
        cfg = app.extensions[_EXT_KEY]
        endpoint = request.endpoint or request.path
        # Default-deny baseline: an endpoint with no explicit policy inherits the baseline (AC-03).
        limit: Limit = cfg["endpoint_limits"].get(endpoint, cfg["baseline"])
        key = f"{identity()}|{endpoint}"
        if not cfg["limiter"].check(key, limit):
            return _too_many(limit)
        return None


def _too_many(limit: Limit):  # type: ignore[no-untyped-def]
    # Non-disclosing 429: only a Retry-After, no internal limit detail (AC-05, DESIGN §6).
    resp = jsonify({"error": "rate_limited"})
    resp.status_code = 429
    resp.headers["Retry-After"] = str(limit.window_seconds)
    return resp


def concurrency_guard(op: str, cap: int, user_id: str):
    """Context manager bounding concurrent quota/IO-heavy work per user (import/export).

    Raises ``TooManyConcurrent`` (429-mapped) if the cap is exceeded, starting no work.
    """
    cfg = current_app.extensions[_EXT_KEY]
    capper: ConcurrencyCap = cfg["concurrency"]
    key = f"{user_id}|{op}"

    class _Slot:
        def __enter__(self) -> _Slot:
            if not capper.try_acquire(key, cap):
                g.concurrency_rejected = True
                raise TooManyConcurrent(op)
            return self

        def __exit__(self, *exc: object) -> None:
            capper.release(key)

    return _Slot()


class TooManyConcurrent(Exception):
    """Raised when a per-user concurrency cap is exceeded (maps to 429)."""
