"""Body-size cap (issue 020) and CSRF (issue 026) middleware tests."""

from __future__ import annotations

from pingpals_api.app import create_app
from pingpals_api.config import SECRET_KEY_NAME, MappingSecretStore, TestConfig
from pingpals_api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME

GOOD_SECRET = "unit-test-secret-key-0123456789abcdef"


def _app(**overrides):
    class Cfg(TestConfig):
        pass

    for k, v in overrides.items():
        setattr(Cfg, k, v)
    app = create_app(Cfg(), MappingSecretStore({SECRET_KEY_NAME: GOOD_SECRET}))
    app.config["PROPAGATE_EXCEPTIONS"] = False
    state = {"written": False}

    @app.post("/contacts")
    def _create():  # type: ignore[no-untyped-def]
        state["written"] = True
        return {"ok": True}

    return app, state


# ---- Body size cap (issue 020 AC-02) ----

def test_oversized_body_rejected_413_before_handler() -> None:
    app, state = _app(MAX_CONTENT_LENGTH=64)
    resp = app.test_client().post(
        "/contacts",
        data=b"x" * 256,
        headers={"Sec-Fetch-Site": "same-origin"},  # pass CSRF so 413 is the cause under test
    )
    assert resp.status_code == 413
    assert state["written"] is False  # rejected before any business logic ran


# ---- CSRF (issue 026) ----

def test_cross_site_mutation_without_signal_denied() -> None:
    app, state = _app()
    resp = app.test_client().post("/contacts", headers={"Sec-Fetch-Site": "cross-site"})
    assert resp.status_code == 403  # AC-01
    assert state["written"] is False


def test_missing_csrf_signal_denied() -> None:
    app, state = _app()
    resp = app.test_client().post("/contacts")  # no token, no Origin, no Sec-Fetch-Site
    assert resp.status_code == 403  # AC-03 fail closed
    assert state["written"] is False


def test_same_origin_fetch_accepted() -> None:
    app, state = _app()
    resp = app.test_client().post("/contacts", headers={"Sec-Fetch-Site": "same-origin"})
    assert resp.status_code == 200  # AC-02
    assert state["written"] is True


def test_double_submit_token_accepted() -> None:
    app, _ = _app()
    client = app.test_client()
    client.set_cookie(CSRF_COOKIE_NAME, "tok-abc123")
    resp = client.post("/contacts", headers={CSRF_HEADER_NAME: "tok-abc123"})
    assert resp.status_code == 200  # AC-02 (double-submit path)


def test_double_submit_mismatch_denied() -> None:
    app, _ = _app()
    client = app.test_client()
    client.set_cookie(CSRF_COOKIE_NAME, "tok-abc123")
    resp = client.post("/contacts", headers={CSRF_HEADER_NAME: "different"})
    assert resp.status_code == 403  # AC-03


def test_cors_allowlist_does_not_satisfy_csrf() -> None:
    # AC-05: independence — an allowlisted Origin with a cross-site fetch signal is still denied.
    app, _ = _app(CORS_ALLOWED_ORIGINS=("https://app.pingpals.example",))
    resp = app.test_client().post(
        "/contacts",
        headers={"Origin": "https://app.pingpals.example", "Sec-Fetch-Site": "cross-site"},
    )
    assert resp.status_code == 403


def test_safe_methods_not_blocked() -> None:
    app, _ = _app()
    assert app.test_client().get("/healthz").status_code == 200
