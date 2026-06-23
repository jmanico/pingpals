"""HTTP boundary hardening — security headers, strict CSP, CORS, TLS enforcement (issue 019).

Every response leaving the Flask trust boundary carries the enforced policy (SECURITY.md §1,
SEC-5.1, FE-1.4, NFR-1.3). Fail closed: a plaintext request is rejected (not redirected) when TLS
is required, and CORS reflects only an exact-match allowlisted origin — never ``*``, never a
blind ``Origin`` echo.
"""

from __future__ import annotations

from flask import Flask, Request, Response, request

# Strict CSP: no inline script, no inline event handlers, no eval, no data:/wildcard script source.
# 'self' only for scripts/styles; the SPA ships no inline script and self-hosts fonts (FE-1.4/1.8).
_CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self'",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'none'",
        "frame-ancestors 'none'",
        "form-action 'self'",
    ]
)

# Restrictive Permissions-Policy: deny powerful features by default.
_PERMISSIONS_POLICY = ", ".join(
    f"{feature}=()" for feature in ("camera", "microphone", "geolocation", "payment", "usb")
)


def _is_secure(req: Request) -> bool:
    """True if the request reached us over TLS (honouring a trusted forwarding proxy)."""
    if req.is_secure:
        return True
    return req.headers.get("X-Forwarded-Proto", "").lower() == "https"


def register_http_boundary(app: Flask) -> None:
    """Install the TLS-enforcement guard, security-header/CSP emitter, and CORS handler."""

    require_tls: bool = app.config.get("REQUIRE_TLS", True)
    allowed_origins: tuple[str, ...] = tuple(app.config.get("CORS_ALLOWED_ORIGINS", ()))

    @app.before_request
    def _enforce_tls():  # type: ignore[no-untyped-def]
        # Reject plaintext rather than redirecting (SEC-5.1, AC-01). TLS 1.3 negotiation itself is
        # enforced at the terminator; the app re-asserts that the hop was secure.
        if require_tls and not _is_secure(request):
            return _plaintext_rejected()
        return None

    @app.after_request
    def _apply_security_headers(response: Response) -> Response:
        response.headers["Content-Security-Policy"] = _CSP
        response.headers["Strict-Transport-Security"] = (
            f"max-age={app.config.get('HSTS_MAX_AGE', 63072000)}; includeSubDomains; preload"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = _PERMISSIONS_POLICY
        response.headers["X-Frame-Options"] = "DENY"
        response.headers.pop("Server", None)  # don't leak the framework banner (NFR-1.3)
        _apply_cors(response, allowed_origins)
        return response


def _apply_cors(response: Response, allowed_origins: tuple[str, ...]) -> None:
    """Exact-match, credentialed CORS. No origin reflection, never ``*`` (SEC §1, AC-03/AC-06)."""
    origin = request.headers.get("Origin")
    if origin and origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
        response.headers.setdefault("Access-Control-Allow-Headers", "Content-Type, X-CSRF-Token")
        response.headers.setdefault(
            "Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE"
        )
    # A non-allowlisted origin gets NO ACAO header at all — the browser denies the read.


def _plaintext_rejected():  # type: ignore[no-untyped-def]
    from flask import jsonify

    resp = jsonify({"error": "tls_required"})
    resp.status_code = 400
    return resp
