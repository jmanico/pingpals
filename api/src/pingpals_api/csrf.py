"""CSRF protection for mutating routes (issue 026, SECURITY.md §3, SEC-2.3).

Cookie-borne sessions are auto-attached cross-site, so every state-changing request
(POST/PUT/PATCH/DELETE) needs an affirmative anti-CSRF signal beyond SameSite. This guard accepts
EITHER a valid double-submit token (``X-CSRF-Token`` header equal to the ``csrf_token`` cookie,
constant-time compared) OR a strict same-origin signal (``Sec-Fetch-Site: same-origin`` or an
exact-match allowlisted ``Origin``). It FAILS CLOSED: a missing/malformed/unverifiable signal is
denied with 403 and no write occurs. This is independent of the CORS response policy (issue 019).
"""

from __future__ import annotations

import hmac
import secrets

from flask import Flask, abort, request

CSRF_COOKIE_NAME = "csrf_token"  # noqa: S105 — cookie name, not a secret value
CSRF_HEADER_NAME = "X-CSRF-Token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

#: Endpoints intentionally exempt (e.g. signature-verified webhooks). Empty by default; a mutating
#: route cannot silently opt out (issue 026 AC-04 asserts this set stays intentional).
CSRF_EXEMPT_ENDPOINTS: frozenset[str] = frozenset()


def issue_csrf_token() -> str:
    """Return a fresh, unguessable CSRF token for the double-submit cookie/header pair."""
    return secrets.token_urlsafe(32)


def _double_submit_ok() -> bool:
    cookie = request.cookies.get(CSRF_COOKIE_NAME)
    header = request.headers.get(CSRF_HEADER_NAME)
    if not cookie or not header:
        return False
    return hmac.compare_digest(cookie, header)


def _same_origin_ok(allowed_origins: frozenset[str]) -> bool:
    fetch_site = request.headers.get("Sec-Fetch-Site")
    if fetch_site == "same-origin":
        return True
    if fetch_site in {"cross-site", "same-site"}:
        return False  # explicit cross/loose-site signal — deny regardless of Origin
    origin = request.headers.get("Origin")
    return bool(origin) and origin in allowed_origins


def register_csrf(app: Flask) -> None:
    allowed_origins = frozenset(app.config.get("CORS_ALLOWED_ORIGINS", ()))

    @app.before_request
    def _enforce_csrf():  # type: ignore[no-untyped-def]
        if request.method in SAFE_METHODS:
            return None
        if request.endpoint in CSRF_EXEMPT_ENDPOINTS:
            return None
        if _double_submit_ok() or _same_origin_ok(allowed_origins):
            return None
        abort(403)  # fail closed (SEC-2.3) — no write happens
        return None
