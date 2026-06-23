"""HTTP-boundary tests — headers, strict CSP, CORS, TLS enforcement (issue 019 / REQ-FND-008)."""

from __future__ import annotations

from pingpals_api.app import create_app
from pingpals_api.config import (
    SECRET_KEY_NAME,
    Config,
    MappingSecretStore,
    ProductionConfig,
    TestConfig,
)

GOOD_SECRET = "unit-test-secret-key-0123456789abcdef"
ALLOWED = "https://app.pingpals.example"


def _store() -> MappingSecretStore:
    return MappingSecretStore({SECRET_KEY_NAME: GOOD_SECRET})


def _client(config: Config):
    return create_app(config, _store()).test_client()


class CorsTestConfig(TestConfig):
    CORS_ALLOWED_ORIGINS = (ALLOWED,)


def test_security_headers_present_and_csp_strict() -> None:
    resp = _client(TestConfig()).get("/healthz")
    h = resp.headers
    assert resp.status_code == 200
    csp = h["Content-Security-Policy"]
    # AC-02: strict CSP — no inline, no eval, no data:/wildcard script source.
    assert "script-src 'self'" in csp
    assert "'unsafe-inline'" not in csp
    assert "'unsafe-eval'" not in csp
    assert "data:" not in csp
    assert "*" not in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["Referrer-Policy"] == "no-referrer"
    assert "max-age=" in h["Strict-Transport-Security"]
    assert h["Permissions-Policy"]
    assert h["X-Frame-Options"] == "DENY"


def test_cors_reflects_only_allowlisted_origin() -> None:
    client = _client(CorsTestConfig())
    resp = client.get("/healthz", headers={"Origin": ALLOWED})
    assert resp.headers.get("Access-Control-Allow-Origin") == ALLOWED  # AC-03
    assert resp.headers.get("Access-Control-Allow-Credentials") == "true"


def test_cors_denies_non_allowlisted_origin() -> None:
    client = _client(CorsTestConfig())
    resp = client.get("/healthz", headers={"Origin": "https://evil.example"})
    # AC-06: no reflection, no wildcard.
    assert "Access-Control-Allow-Origin" not in resp.headers


def test_cors_never_wildcard_even_without_allowlist() -> None:
    resp = _client(TestConfig()).get("/healthz", headers={"Origin": "https://evil.example"})
    assert resp.headers.get("Access-Control-Allow-Origin") != "*"
    assert "Access-Control-Allow-Origin" not in resp.headers


def test_plaintext_rejected_when_tls_required() -> None:
    # ProductionConfig requires TLS; the test client speaks plaintext http.
    resp = _client(ProductionConfig()).get("/healthz")
    assert resp.status_code == 400  # AC-01: rejected, not redirected (no 3xx)
    assert resp.get_json() == {"error": "tls_required"}


def test_forwarded_https_is_accepted() -> None:
    resp = _client(ProductionConfig()).get("/healthz", headers={"X-Forwarded-Proto": "https"})
    assert resp.status_code == 200
