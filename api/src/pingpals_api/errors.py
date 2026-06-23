"""Least-information error handlers (issue 018/019, NFR-1.3, SEC §6).

Responses never leak a stack trace, framework banner, or internal hostname. User-facing copy stays
gentle (DESIGN.md §6) without softening a validation failure into ambiguity (FR-1.4).
"""

from __future__ import annotations

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from .rate_limit import TooManyConcurrent

# Stable, non-disclosing messages keyed by status. No internal detail.
_GENERIC = {
    400: "bad_request",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    413: "payload_too_large",
    429: "rate_limited",
    500: "internal_error",
}


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def _handle_http_exception(exc: HTTPException):  # type: ignore[no-untyped-def]
        code = exc.code or 500
        resp = jsonify({"error": _GENERIC.get(code, "error")})
        resp.status_code = code
        return resp

    @app.errorhandler(TooManyConcurrent)
    def _handle_concurrency(_exc: TooManyConcurrent):  # type: ignore[no-untyped-def]
        # Per-user concurrency cap exceeded — non-disclosing 429 (issue 024 AC-02/AC-05).
        resp = jsonify({"error": _GENERIC[429]})
        resp.status_code = 429
        return resp

    @app.errorhandler(Exception)
    def _handle_unexpected(_exc: Exception):  # type: ignore[no-untyped-def]
        # AC-06: an unhandled error returns no stack trace / banner / hostname.
        resp = jsonify({"error": _GENERIC[500]})
        resp.status_code = 500
        return resp
