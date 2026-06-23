"""Internal east-west message authentication tests (issue 027 / REQ-FND-016)."""

from __future__ import annotations

import dataclasses

from pingpals_api.audit.sink import RecordingAuditSink
from pingpals_api.internal_authn import WorkItemConsumer, sign

KEY = b"internal-shared-mac-key-0123456789ab"


class Clock:
    def __init__(self, t: int = 1000) -> None:
        self.t = t

    def __call__(self) -> int:
        return self.t


def _consumer(clock: Clock, owner_authorized=lambda producer, owner: True):
    audit = RecordingAuditSink()
    dlq: list[tuple] = []
    consumer = WorkItemConsumer(
        key=KEY,
        audit=audit,
        dead_letter=lambda env, reason: dlq.append((env, reason)),
        owner_authorized=owner_authorized,
        time_source=clock,
    )
    return consumer, audit, dlq


def _env(clock: Clock, owner="alice", producer="scheduler", nonce="n1", payload=None):
    payload = payload or {"reminder_id": "r1"}
    return sign(KEY, producer, owner, payload, nonce, clock.t)


def test_legitimate_item_processed_exactly_once() -> None:
    clock = Clock()
    consumer, _, dlq = _consumer(clock)
    delivered: list[tuple] = []
    env = _env(clock)
    assert consumer.consume(env, lambda p, o: delivered.append((p, o))) is True  # AC-02
    assert delivered == [({"reminder_id": "r1"}, "alice")]
    assert dlq == []


def test_forged_mac_rejected_and_dead_lettered() -> None:
    clock = Clock()
    consumer, audit, dlq = _consumer(clock)
    forged = dataclasses.replace(_env(clock), mac="deadbeef")
    delivered: list = []
    assert consumer.consume(forged, lambda p, o: delivered.append(1)) is False  # AC-01/AC-03
    assert delivered == []
    assert dlq and dlq[0][1] == "integrity"
    assert any(e.action == "internal.rejected" for e in audit.events)  # AC-06


def test_tampered_owner_rejected() -> None:
    clock = Clock()
    consumer, _, dlq = _consumer(clock)
    # Re-point the envelope to another user without re-signing -> MAC mismatch.
    tampered = dataclasses.replace(_env(clock, owner="alice"), owner_id="bob")
    assert consumer.consume(tampered, lambda p, o: None) is False
    assert dlq[0][1] == "integrity"


def test_replayed_item_rejected() -> None:
    clock = Clock()
    consumer, _, dlq = _consumer(clock)
    env = _env(clock)
    assert consumer.consume(env, lambda p, o: None) is True
    # Same nonce again -> replay (AC-04): no duplicate delivery.
    delivered: list = []
    assert consumer.consume(env, lambda p, o: delivered.append(1)) is False
    assert delivered == []
    assert dlq[0][1] == "replay"


def test_stale_item_rejected() -> None:
    clock = Clock()
    consumer, _, dlq = _consumer(clock)
    env = _env(clock)
    clock.t += 10_000  # far beyond the TTL window
    assert consumer.consume(env, lambda p, o: None) is False
    assert dlq[0][1] == "stale"


def test_owner_not_entitled_is_denied() -> None:
    # AC-05 / FR-5.5: producer entitled only for alice; an item asserting bob is denied.
    clock = Clock()
    consumer, audit, dlq = _consumer(
        clock, owner_authorized=lambda producer, owner: owner == "alice"
    )
    env = _env(clock, owner="bob", nonce="n2")
    delivered: list = []
    assert consumer.consume(env, lambda p, o: delivered.append(1)) is False
    assert delivered == []
    assert dlq[0][1] == "authz"
    assert any(e.purpose == "authz" for e in audit.events)
