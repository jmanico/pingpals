"""Per-request authorization decision point (issue 025, SEC-2.1/2.2/2.3, ARCH Rules 1 & 3).

A central PDP evaluates BOTH object-level (the subject owns the target — no BOLA) and
function-level (the subject may invoke the operation — no BFLA) authorization on every request,
with no trust from prior auth or network position. Any indeterminate or errored decision DENIES
(fail closed) and the denial is recorded in the audit log (SEC-8.1). The React client makes no
authorization decision — the server PDP is authoritative (ARCH Rule 1).

Until the auth tier (issues 017-023) wires a real principal resolver, the default resolver returns
``None`` and every protected route denies — which is the correct fail-closed default.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any

from flask import Flask, abort, current_app

from .audit.sink import AuditEvent, AuditSink

_EXT_KEY = "pingpals_authz"


@dataclass(frozen=True)
class Principal:
    """The authenticated subject. ``capabilities`` are the functions it may invoke (BFLA gate)."""

    user_id: str
    capabilities: frozenset[str]


class PolicyDecisionPoint:
    def __init__(self, audit: AuditSink) -> None:
        self._audit = audit

    def authorize(
        self,
        principal: Principal | None,
        function: str,
        resource_owner_id: str | None = None,
    ) -> bool:
        try:
            if principal is None:
                return self._deny("anonymous", function, "no_principal")
            if function not in principal.capabilities:
                return self._deny(principal.user_id, function, "bfla")  # function-level
            if resource_owner_id is not None and resource_owner_id != principal.user_id:
                return self._deny(principal.user_id, function, "bola")  # object-level
            return True
        except Exception:  # indeterminate/errored policy -> deny (SEC-2.3)
            pid = getattr(principal, "user_id", "anonymous")
            return self._deny(pid, function, "policy_error")

    def _deny(self, principal_id: str, function: str, reason: str) -> bool:
        self._audit.record(AuditEvent("authz.denied", principal_id, function, "denied", reason))
        return False


def register_authorization(
    app: Flask,
    principal_provider: Callable[[], Principal | None],
    audit: AuditSink,
) -> None:
    """Install the PDP and the request-time principal resolver on the app."""
    app.extensions[_EXT_KEY] = {
        "pdp": PolicyDecisionPoint(audit),
        "principal": principal_provider,
    }


def require_authorization(
    function: str,
    owner_loader: Callable[..., str | None] | None = None,
):
    """Decorator: evaluate object+function authorization before the view runs (fail closed).

    ``owner_loader(**view_kwargs)`` returns the owning user id of the targeted object, enabling the
    object-level (BOLA) check. A cross-user object resolves to 404 (not-found); an unauthenticated
    or function-denied request resolves to 403.
    """

    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cfg = current_app.extensions[_EXT_KEY]
            principal: Principal | None = cfg["principal"]()  # resolved per request, never trusted
            owner_id = owner_loader(**kwargs) if owner_loader is not None else None
            if not cfg["pdp"].authorize(principal, function, owner_id):
                # Don't reveal existence of another user's object: not-found on object mismatch.
                abort(404 if (principal is not None and owner_id is not None) else 403)
            return view(*args, **kwargs)

        return wrapper

    return decorator
