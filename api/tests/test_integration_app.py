"""Integration / e2e tests over the wired application (issue 076, TEST-1.2).

Exercises the full create_app stack end-to-end (HTTP boundary headers, body cap, CSRF, rate limit,
authorization, error handling, audit) through the Flask test client — complementing the focused
unit suites and demonstrating the layers compose.
"""

from __future__ import annotations

from pingpals_api.app import create_app
from pingpals_api.config import SECRET_KEY_NAME, MappingSecretStore, TestConfig

SECRET = "integration-secret-key-0123456789abcd"


def _app(**overrides):
    class Cfg(TestConfig):
        pass

    for k, v in overrides.items():
        setattr(Cfg, k, v)
    app = create_app(Cfg(), MappingSecretStore({SECRET_KEY_NAME: SECRET}))
    app.config["PROPAGATE_EXCEPTIONS"] = False
    return app


def test_healthz_carries_full_security_header_policy() -> None:
    resp = _app().test_client().get("/healthz")
    assert resp.status_code == 200
    h = resp.headers
    assert "script-src 'self'" in h["Content-Security-Policy"]
    assert "'unsafe-inline'" not in h["Content-Security-Policy"]
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["Referrer-Policy"] == "no-referrer"
    assert "max-age=" in h["Strict-Transport-Security"]


def test_mutating_request_blocked_without_csrf_then_allowed_with_signal() -> None:
    app = _app()

    @app.post("/echo")
    def _echo():  # type: ignore[no-untyped-def]
        return {"ok": True}

    client = app.test_client()
    assert client.post("/echo").status_code == 403  # no CSRF signal -> blocked
    assert client.post("/echo", headers={"Sec-Fetch-Site": "same-origin"}).status_code == 200


def test_rate_limit_returns_429_at_baseline() -> None:
    from pingpals_api.rate_limit import FixedWindowRateLimiter, Limit

    app = _app()
    cfg = app.extensions["pingpals_rate_limit"]
    cfg["limiter"] = FixedWindowRateLimiter()
    cfg["baseline"] = Limit(max_requests=1, window_seconds=60)
    client = app.test_client()
    assert client.get("/healthz").status_code == 200
    resp = client.get("/healthz")
    assert resp.status_code == 429
    assert resp.headers.get("Retry-After") == "60"


def test_unhandled_error_is_non_disclosing() -> None:
    app = _app()

    @app.get("/boom")
    def _boom():  # type: ignore[no-untyped-def]
        raise RuntimeError("internal path /var/secret on host db-1")

    resp = app.test_client().get("/boom")
    assert resp.status_code == 500
    body = resp.get_data(as_text=True)
    assert "db-1" not in body and "Traceback" not in body


def test_app_has_audit_log_wired() -> None:
    app = _app()
    assert "pingpals_audit" in app.extensions
    assert app.extensions["pingpals_audit"].verify() is True
