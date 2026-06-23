"""Application configuration + secret-store adapter (REQ-FND-007 / issue 018, SECURITY.md §8/§2).

Hardened, fail-closed defaults. ``SECRET_KEY`` is loaded at runtime from a ``SecretStore`` adapter
(never a literal, never baked into the image or a build arg — SEC-3.2). Non-dev configs refuse to
start without a strong secret or with the debugger enabled (the factory enforces this).
"""

from __future__ import annotations

import os
from typing import Protocol, runtime_checkable

#: Logical name of the session-signing secret in the secret store.
SECRET_KEY_NAME = "PINGPALS_SECRET_KEY"  # noqa: S105 — this is the key's NAME, not a secret value
#: Minimum acceptable secret length (bytes) — defends against weak/guessable keys (CWE-330).
MIN_SECRET_KEY_LENGTH = 32


@runtime_checkable
class SecretStore(Protocol):
    """Adapter to the managed secret store. The concrete vendor is `TO BE DECIDED`.

    In a deployed environment the orchestrator injects secrets at runtime (e.g. mounted file or
    env var sourced FROM the managed store) — they are never committed or baked into image layers.
    """

    def get_secret(self, name: str) -> str | None:
        """Return the secret value for ``name`` or ``None`` if absent."""


class EnvSecretStore:
    """Default adapter: reads runtime-injected secrets from the process environment.

    The value is injected by the deployment from the managed secret store; it is NOT a hard-coded
    literal and is NOT baked into the image (the Dockerfile sets no secret — REQ-FND-002).
    """

    def get_secret(self, name: str) -> str | None:
        value = os.environ.get(name)
        return value or None


class MappingSecretStore:
    """In-memory adapter for tests/local — secrets passed explicitly, never persisted."""

    def __init__(self, secrets: dict[str, str]) -> None:
        self._secrets = dict(secrets)

    def get_secret(self, name: str) -> str | None:
        return self._secrets.get(name) or None


class Config:
    """Base, hardened, production-safe defaults."""

    ENV_NAME = "production"
    IS_DEV = False
    DEBUG = False
    TESTING = False

    #: Reject plaintext HTTP at the boundary rather than silently redirecting (SEC-5.1).
    REQUIRE_TLS = True

    #: Exact-match CORS allowlist for credentialed routes. Empty = same-origin only (SEC §1).
    CORS_ALLOWED_ORIGINS: tuple[str, ...] = ()

    #: Cookie session hardening (SEC-1.2). Secure cookies require HTTPS in deployed envs.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"

    #: HSTS max-age (seconds) — 2 years, with subdomains.
    HSTS_MAX_AGE = 63072000


class ProductionConfig(Config):
    ENV_NAME = "production"


class DevelopmentConfig(Config):
    """Local development only — relaxes TLS enforcement and Secure-cookie requirement.

    ``IS_DEV`` is the ONLY switch that permits a missing secret or ``debug=True``; it must never be
    set in a deployed build.
    """

    ENV_NAME = "development"
    IS_DEV = True
    REQUIRE_TLS = False
    SESSION_COOKIE_SECURE = False


class TestConfig(Config):
    """Test config: full non-dev hardening (secret still required) but TLS check relaxed."""

    ENV_NAME = "test"
    TESTING = True
    REQUIRE_TLS = False
    SESSION_COOKIE_SECURE = False
