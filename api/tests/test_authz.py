"""Authorization decision-point tests (issue 025 / REQ-FND-014)."""

from __future__ import annotations

from pingpals_api.app import create_app
from pingpals_api.audit.sink import RecordingAuditSink
from pingpals_api.authz import (
    PolicyDecisionPoint,
    Principal,
    register_authorization,
    require_authorization,
)
from pingpals_api.config import SECRET_KEY_NAME, MappingSecretStore, TestConfig

GOOD_SECRET = "unit-test-secret-key-0123456789abcdef"


class _BadCaps:
    def __contains__(self, _item: object) -> bool:
        raise RuntimeError("policy backend down")


def _pdp() -> tuple[PolicyDecisionPoint, RecordingAuditSink]:
    audit = RecordingAuditSink()
    return PolicyDecisionPoint(audit), audit


def test_allows_owner_with_capability() -> None:
    pdp, _ = _pdp()
    alice = Principal("alice", frozenset({"contact.read"}))
    assert pdp.authorize(alice, "contact.read", resource_owner_id="alice") is True  # AC-01


def test_cross_user_object_denied_and_audited() -> None:
    pdp, audit = _pdp()
    alice = Principal("alice", frozenset({"contact.read"}))
    assert pdp.authorize(alice, "contact.read", resource_owner_id="bob") is False  # AC-02 BOLA
    assert any(e.action == "authz.denied" and e.purpose == "contact.read" for e in audit.events)


def test_missing_capability_denied_bfla() -> None:
    pdp, audit = _pdp()
    alice = Principal("alice", frozenset())  # no capabilities
    assert pdp.authorize(alice, "contact.delete", resource_owner_id="alice") is False  # AC-04
    assert audit.events[-1].action == "authz.denied"


def test_no_principal_denied() -> None:
    pdp, audit = _pdp()
    assert pdp.authorize(None, "contact.read") is False
    assert audit.events[-1].principal == "anonymous"


def test_indeterminate_policy_fails_closed() -> None:
    pdp, audit = _pdp()
    faulty = Principal.__new__(Principal)
    object.__setattr__(faulty, "user_id", "alice")
    object.__setattr__(faulty, "capabilities", _BadCaps())
    assert pdp.authorize(faulty, "contact.read") is False  # AC-03 fail closed
    assert audit.events[-1].outcome == "denied"


# ---- Flask integration: server enforces regardless of client (AC-05/AC-06) ----

def _app(principal):
    app = create_app(TestConfig(), MappingSecretStore({SECRET_KEY_NAME: GOOD_SECRET}))
    audit = app.extensions["pingpals_audit"]
    register_authorization(app, principal_provider=lambda: principal, audit=audit)

    @app.get("/contacts/<cid>")
    @require_authorization("contact.read", owner_loader=lambda cid: _OWNER.get(cid))
    def _read(cid):  # type: ignore[no-untyped-def]
        return {"id": cid}

    return app


_OWNER = {"c-alice": "alice", "c-bob": "bob"}


def test_endpoint_allows_owner() -> None:
    app = _app(Principal("alice", frozenset({"contact.read"})))
    assert app.test_client().get("/contacts/c-alice").status_code == 200


def test_endpoint_cross_user_is_not_found() -> None:
    app = _app(Principal("alice", frozenset({"contact.read"})))
    assert app.test_client().get("/contacts/c-bob").status_code == 404  # AC-02 (not-found)


def test_endpoint_unauthenticated_denied() -> None:
    app = _app(None)
    assert app.test_client().get("/contacts/c-alice").status_code == 403  # AC-05/AC-06
