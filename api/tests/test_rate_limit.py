"""Rate-limit + concurrency-cap tests (issue 024 / REQ-FND-013)."""

from __future__ import annotations

import pytest

from pingpals_api.app import create_app
from pingpals_api.config import SECRET_KEY_NAME, MappingSecretStore, TestConfig
from pingpals_api.rate_limit import (
    ConcurrencyCap,
    FixedWindowRateLimiter,
    Limit,
    TooManyConcurrent,
    concurrency_guard,
)

GOOD_SECRET = "unit-test-secret-key-0123456789abcdef"


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def test_fixed_window_allows_then_denies_then_resets() -> None:
    clock = FakeClock()
    limiter = FixedWindowRateLimiter(clock=clock)
    limit = Limit(max_requests=2, window_seconds=60)
    assert limiter.check("k", limit) is True
    assert limiter.check("k", limit) is True
    assert limiter.check("k", limit) is False  # 3rd exceeds
    clock.t = 61
    assert limiter.check("k", limit) is True   # new window


def test_concurrency_cap_rejects_excess_without_starting_work() -> None:
    cap = ConcurrencyCap()
    assert cap.try_acquire("alice|import", 1) is True
    assert cap.try_acquire("alice|import", 1) is False  # AC-02: excess rejected
    cap.release("alice|import")
    assert cap.try_acquire("alice|import", 1) is True


def _app(**ext):
    app = create_app(TestConfig(), MappingSecretStore({SECRET_KEY_NAME: GOOD_SECRET}))
    cfg = app.extensions["pingpals_rate_limit"]
    cfg["limiter"] = FixedWindowRateLimiter()  # fresh counters
    cfg.update(ext)
    return app


def test_baseline_applies_to_unlisted_endpoint() -> None:
    # AC-03: an endpoint with no explicit policy is throttled at the baseline, not unbounded.
    app = _app(baseline=Limit(max_requests=2, window_seconds=60))
    client = app.test_client()
    assert client.get("/healthz").status_code == 200
    assert client.get("/healthz").status_code == 200
    resp = client.get("/healthz")
    assert resp.status_code == 429  # AC-01
    assert resp.headers.get("Retry-After") == "60"  # AC-05 minimal disclosure
    assert resp.get_json() == {"error": "rate_limited"}


def test_sensitive_endpoint_gets_tighter_limit() -> None:
    # AC-04: a sensitive endpoint (e.g. auth) is limited more strictly than baseline.
    app = _app(
        baseline=Limit(max_requests=100, window_seconds=60),
        endpoint_limits={"health.healthz": Limit(max_requests=1, window_seconds=60)},
    )
    client = app.test_client()
    assert client.get("/healthz").status_code == 200
    assert client.get("/healthz").status_code == 429


def test_concurrency_guard_maps_to_429() -> None:
    app = _app()
    cap: ConcurrencyCap = app.extensions["pingpals_rate_limit"]["concurrency"]
    cap.try_acquire("alice|export", 1)  # pre-fill the single slot

    @app.get("/export")
    def _export():  # type: ignore[no-untyped-def]
        with concurrency_guard("export", cap=1, user_id="alice"):
            return {"ok": True}

    assert app.test_client().get("/export").status_code == 429


def test_concurrency_guard_releases_slot() -> None:
    app = _app()
    with app.test_request_context():
        with concurrency_guard("export", cap=1, user_id="bob"):
            pass
        # slot released on exit -> a second acquisition succeeds
        with concurrency_guard("export", cap=1, user_id="bob"):
            pass


def test_concurrency_guard_raises_when_full() -> None:
    app = _app()
    cap: ConcurrencyCap = app.extensions["pingpals_rate_limit"]["concurrency"]
    cap.try_acquire("carol|import", 1)
    with app.test_request_context():  # noqa: SIM117
        with pytest.raises(TooManyConcurrent):
            with concurrency_guard("import", cap=1, user_id="carol"):
                pass
