"""Request-body size cap at the HTTP boundary (issue 020, SEC-4.1 §4 / SEC-6.x).

An oversized request is rejected with 413 BEFORE deserialization and without buffering the full
payload into memory. Two layers: Werkzeug's ``MAX_CONTENT_LENGTH`` (enforced as the stream is
read) plus an explicit ``Content-Length`` pre-check in ``before_request`` so the rejection happens
before any business logic runs. Fail closed — never truncate or partially read.
"""

from __future__ import annotations

from flask import Flask, abort, request

#: Default hard cap for a request body (1 MiB) — generous for JSON, bounded against DoS.
DEFAULT_MAX_BODY_BYTES = 1 * 1024 * 1024


def register_body_limit(app: Flask) -> None:
    max_bytes: int = app.config.get("MAX_CONTENT_LENGTH") or DEFAULT_MAX_BODY_BYTES
    app.config["MAX_CONTENT_LENGTH"] = max_bytes  # Werkzeug enforces during stream read

    @app.before_request
    def _reject_oversized_body():  # type: ignore[no-untyped-def]
        # Reject on the declared Content-Length before reading/parsing the body (AC-02).
        length = request.content_length
        if length is not None and length > max_bytes:
            abort(413)
        return None
