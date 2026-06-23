"""Health/liveness blueprint (issue 018).

A minimal unauthenticated endpoint that carries no personal data — used for liveness probes and as
a concrete surface for boundary/header tests. It exposes no version banner or internal detail.
"""

from __future__ import annotations

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/healthz")
def healthz():  # type: ignore[no-untyped-def]
    return jsonify({"status": "ok"})
