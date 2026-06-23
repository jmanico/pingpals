"""App-factory hardening tests (issue 018 / REQ-FND-007)."""

from __future__ import annotations

import pytest

from pingpals_api.app import StartupError, create_app
from pingpals_api.config import (
    SECRET_KEY_NAME,
    Config,
    MappingSecretStore,
    TestConfig,
)

GOOD_SECRET = "unit-test-secret-key-0123456789abcdef"  # >= 32 chars


def _store(secret: str | None = GOOD_SECRET) -> MappingSecretStore:
    return MappingSecretStore({SECRET_KEY_NAME: secret} if secret else {})


def test_debug_false_in_non_dev_build() -> None:
    app = create_app(TestConfig(), _store())
    assert app.debug is False  # AC-01


def test_secret_key_loaded_from_store_not_literal() -> None:
    app = create_app(TestConfig(), _store())
    assert app.config["SECRET_KEY"] == GOOD_SECRET  # AC-02


def test_fail_closed_when_secret_missing() -> None:
    with pytest.raises(StartupError):  # AC-03
        create_app(TestConfig(), _store(None))


def test_fail_closed_when_secret_too_weak() -> None:
    with pytest.raises(StartupError):
        create_app(TestConfig(), _store("short"))


def test_fail_closed_when_debug_true_in_non_dev() -> None:
    class DebugProd(Config):
        DEBUG = True
        IS_DEV = False

    with pytest.raises(StartupError):  # AC-04
        create_app(DebugProd(), _store())


def test_jinja_autoescape_enabled() -> None:
    app = create_app(TestConfig(), _store())
    assert app.jinja_env.autoescape  # AC-05
    with app.app_context():
        from flask import render_template_string

        rendered = render_template_string("{{ value }}", value="<script>alert(1)</script>")
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered


def test_unhandled_error_is_non_disclosing() -> None:
    app = create_app(TestConfig(), _store())
    app.config["PROPAGATE_EXCEPTIONS"] = False  # exercise the 500 handler, not re-raise

    @app.get("/boom")
    def _boom():  # type: ignore[no-untyped-def]
        raise RuntimeError("secret internal detail /var/secrets/key at host db-primary-1")

    client = app.test_client()
    resp = client.get("/boom")
    assert resp.status_code == 500  # AC-06
    body = resp.get_data(as_text=True)
    assert "secret internal detail" not in body
    assert "db-primary-1" not in body
    assert "Traceback" not in body
    assert resp.get_json() == {"error": "internal_error"}
