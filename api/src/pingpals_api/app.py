"""Application factory (issue 018, SECURITY.md §8/§2).

``create_app`` builds a hardened Flask app: ``debug`` is False in any non-dev build, ``SECRET_KEY``
is loaded from a ``SecretStore`` adapter (never a literal/baked value), Jinja autoescaping stays
on, and the HTTP-boundary policy (issue 019) is installed. The factory FAILS CLOSED at startup if
the secret is absent or the debugger would be enabled in a non-dev build.
"""

from __future__ import annotations

from flask import Flask

from .config import (
    MIN_SECRET_KEY_LENGTH,
    SECRET_KEY_NAME,
    Config,
    EnvSecretStore,
    ProductionConfig,
    SecretStore,
)
from .errors import register_error_handlers
from .http_boundary import register_http_boundary


class StartupError(RuntimeError):
    """Raised when a security-critical startup invariant cannot be established (fail closed)."""


def create_app(config: Config | None = None, secret_store: SecretStore | None = None) -> Flask:
    """Construct and return a hardened Flask application.

    :param config: a ``Config`` instance (defaults to :class:`ProductionConfig`).
    :param secret_store: adapter to the managed secret store (defaults to env-injected secrets).
    """
    config = config or ProductionConfig()
    secret_store = secret_store or EnvSecretStore()

    # Fail closed: the interactive debugger must never be reachable in a deployed build (AC-04).
    if config.DEBUG and not config.IS_DEV:
        raise StartupError("debug mode is not permitted in a non-development build")

    secret = secret_store.get_secret(SECRET_KEY_NAME)
    if not config.IS_DEV and (not secret or len(secret) < MIN_SECRET_KEY_LENGTH):
        # Non-disclosing: do not echo the (absent) secret value (AC-03).
        raise StartupError("a strong SECRET_KEY must be provided by the secret store")

    app = Flask(__name__)
    app.config.from_object(config)
    app.config["SECRET_KEY"] = secret  # sourced from the adapter, never a literal (AC-02)
    app.debug = bool(config.DEBUG and config.IS_DEV)

    # Jinja autoescaping is on by default in Flask (incl. string templates). Verify with an
    # explicit fail-closed check (not `assert`, which `python -O` strips) so HTML is never
    # constructed from untrusted strings (AC-05 / SEC-4.2).
    if not app.jinja_env.autoescape:
        raise StartupError("Jinja autoescaping must remain enabled (SEC-4.2)")

    register_http_boundary(app)
    register_error_handlers(app)
    _register_blueprints(app)
    return app


def _register_blueprints(app: Flask) -> None:
    from .blueprints.health import health_bp

    app.register_blueprint(health_bp)
