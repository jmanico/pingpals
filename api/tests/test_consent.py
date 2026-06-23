"""Consent ledger + fail-closed enforcement tests (issue 045 / REQ-ENGINE-034)."""

from __future__ import annotations

from pingpals_api.audit.sink import RecordingAuditSink
from pingpals_api.consent import (
    ConsentEvent,
    ConsentState,
    InMemoryConsentLedger,
    is_delivery_consented,
)


def _ledger(*events) -> InMemoryConsentLedger:
    led = InMemoryConsentLedger()
    for e in events:
        led.append(e)
    return led


def test_no_record_defaults_to_denied() -> None:
    led = _ledger()
    assert led.effective_state("alice", "email", 100) is ConsentState.DENIED  # AC-01/AC-02


def test_latest_record_wins() -> None:
    led = _ledger(
        ConsentEvent("alice", "email", "grant", 100, "v1", 0),
        ConsentEvent("alice", "email", "withdraw", 200, "v1", 1),
    )
    assert led.effective_state("alice", "email", 250) is ConsentState.DENIED   # AC-03 withdrawn
    assert led.effective_state("alice", "email", 150) is ConsentState.GRANTED  # before withdrawal


def test_integrity_failure_is_indeterminate_no_delivery() -> None:
    led = _ledger(ConsentEvent("alice", "email", "grant", 100, "v1", 0, integrity_ok=False))
    assert led.effective_state("alice", "email", 150) is ConsentState.INDETERMINATE  # AC-05


def test_is_delivery_consented_grants_only_on_active_grant() -> None:
    audit = RecordingAuditSink()
    led = _ledger(ConsentEvent("alice", "email", "grant", 100, "v1", 0))
    assert is_delivery_consented(led, "alice", "email", 150, audit) is True   # AC-03
    assert is_delivery_consented(led, "alice", "sms", 150, audit) is False    # AC-01 no record
    assert any(e.action == "consent.denied" for e in audit.events)            # AC-05 audited


def test_withdrawal_before_delivery_blocks_send() -> None:
    led = _ledger(
        ConsentEvent("alice", "email", "grant", 100, "v1", 0),
        ConsentEvent("alice", "email", "withdraw", 200, "v1", 1),
    )
    assert is_delivery_consented(led, "alice", "email", 300) is False  # AC-04
