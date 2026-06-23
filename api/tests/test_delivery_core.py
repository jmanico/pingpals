"""Delivery worker + endpoints + payload + retry tests (issues 046/047/048/052/053)."""

from __future__ import annotations

import pytest

from pingpals_api.audit.log import TamperEvidentAuditLog
from pingpals_api.consent import ConsentEvent, InMemoryConsentLedger
from pingpals_api.delivery.endpoints import EndpointError, EndpointRegistry
from pingpals_api.delivery.payload import (
    ChannelSurface,
    PayloadError,
    build_payload,
    contains_pii_cleartext,
)
from pingpals_api.delivery.retry import (
    CircuitBreaker,
    DeadLetterFull,
    DeadLetterQueue,
    RetryPolicy,
)
from pingpals_api.delivery.worker import DeliveryWorker, Outcome, ReminderJob


class Clock:
    def __init__(self, t=1000):
        self.t = t

    def now(self):
        self.t += 1
        return self.t


# ---- Endpoints (issue 048) ----

def test_endpoint_register_confirm_eligible() -> None:
    reg = EndpointRegistry()
    ep, proof = reg.register("alice", "email", "alice@example.com")
    assert reg.eligible("alice", "email") is None  # not yet verified (AC-02)
    reg.confirm("alice", ep.id, proof)
    assert reg.eligible("alice", "email").id == ep.id  # AC-01


def test_endpoint_cross_user_and_unauth_rejected() -> None:
    reg = EndpointRegistry()
    ep, proof = reg.register("alice", "email", "a@x")
    with pytest.raises(EndpointError):  # AC-06 unauthenticated
        reg.register("", "email", "x@y")
    with pytest.raises(EndpointError):  # AC-06 cross-user confirm
        reg.confirm("bob", ep.id, proof)


def test_endpoint_revoked_not_eligible() -> None:
    reg = EndpointRegistry()
    ep, proof = reg.register("alice", "email", "a@x")
    reg.confirm("alice", ep.id, proof)
    reg.revoke("alice", ep.id)
    assert reg.eligible("alice", "email") is None  # AC-05


def test_revoke_channel_and_all() -> None:
    reg = EndpointRegistry()
    e1, p1 = reg.register("alice", "email", "a@x")
    e2, p2 = reg.register("alice", "push", "sub")
    reg.confirm("alice", e1.id, p1)
    reg.confirm("alice", e2.id, p2)
    assert reg.revoke_channel_for_user("alice", "email") == 1
    assert reg.eligible("alice", "email") is None and reg.eligible("alice", "push") is not None
    assert reg.revoke_all_for_user("alice") == 1


# ---- Payload confidentiality (issue 047) ----

def test_authenticated_payload_has_display_name() -> None:
    p = build_payload("r1", "inapp", ChannelSurface.AUTHENTICATED, "Alex", "mailto:a@x")
    assert p.display_name == "Alex" and not contains_pii_cleartext(p)  # AC-01


def test_untrusted_surface_is_opaque_only() -> None:
    p = build_payload("r1", "push", ChannelSurface.UNTRUSTED, "Alex", "mailto:a@x")
    assert p.display_name is None and p.outreach_action is None  # AC-02/AC-04
    assert not contains_pii_cleartext(p)


def test_encrypted_body_requires_message_encryption() -> None:
    p = build_payload("r1", "push", ChannelSurface.ENCRYPTED_BODY, "Alex", "x",
                      can_encrypt_message=True)
    assert p.encrypted and p.display_name == "Alex"  # AC-03 PII only in encrypted body
    with pytest.raises(PayloadError):  # AC-07 cannot encrypt -> fail closed
        build_payload("r1", "push", ChannelSurface.ENCRYPTED_BODY, "Alex", "x",
                      can_encrypt_message=False)


# ---- Retry / breaker / DLQ (issue 052) ----

def test_backoff_is_bounded_and_nonzero() -> None:
    policy = RetryPolicy(max_attempts=5, base_delay=1, max_delay=60)
    d = policy.backoff(10, jitter=lambda: 1.0)  # huge attempt
    assert 0 < d <= 60  # bounded (AC-02)
    assert policy.is_exhausted(5) and not policy.is_exhausted(4)


def test_circuit_breaker_trips_and_blocks() -> None:
    cb = CircuitBreaker(threshold=2)
    assert cb.allow("email")
    cb.record_failure("email")
    cb.record_failure("email")
    assert cb.allow("email") is False  # AC-03 tripped
    cb.reset("email")
    assert cb.allow("email") is True


def test_dlq_bounded_alerts_no_silent_drop() -> None:
    alerts: list[str] = []
    dlq = DeadLetterQueue(max_size=1, on_alert=alerts.append)
    dlq.add({"x": 1})
    with pytest.raises(DeadLetterFull):  # AC-04
        dlq.add({"x": 2})
    assert alerts


# ---- Worker (issues 046/053) ----

def _worker(consented=True, endpoint=True):
    audit = TamperEvidentAuditLog(time_source=Clock())
    led = InMemoryConsentLedger()
    if consented:
        led.append(ConsentEvent("alice", "email", "grant", 1, "v1", 0))
    reg = EndpointRegistry()
    if endpoint:
        ep, proof = reg.register("alice", "email", "a@x")
        reg.confirm("alice", ep.id, proof)
    sent: list = []
    worker = DeliveryWorker(audit, led, reg, send=lambda e, p: sent.append((e, p)),
                            now=lambda: 100)
    return worker, audit, sent


def _job(owner="alice", channel="email"):
    return ReminderJob(owner, "r1", channel, ChannelSurface.AUTHENTICATED, "Alex", "mailto:a@x")


def test_delivers_when_owner_endpoint_consent_all_match() -> None:
    worker, _, sent = _worker()
    assert worker.process(_job()) is Outcome.DELIVERED  # AC-01
    assert len(sent) == 1


def test_no_owner_dead_lettered() -> None:
    worker, audit, _ = _worker()
    assert worker.process(_job(owner=None)) is Outcome.DEAD_LETTERED  # AC-04
    assert any(e.action == "delivery.dead_letter" for e in audit.entries)


def test_missing_endpoint_dropped_and_audited() -> None:
    worker, audit, sent = _worker(endpoint=False)
    assert worker.process(_job()) is Outcome.DROPPED  # AC-02
    assert sent == []
    assert any(e.action == "delivery.denied" for e in audit.entries)


def test_withdrawn_consent_dropped() -> None:
    worker, audit, sent = _worker(consented=False)
    assert worker.process(_job()) is Outcome.DROPPED  # AC-03
    assert sent == []


def test_delivery_records_audit_event() -> None:
    worker, audit, _ = _worker()
    worker.process(_job())
    assert any(e.action == "delivery.attempt" and "consent:granted" in (e.object_ref or "")
               for e in audit.entries)  # 042 AC-01/AC-02
