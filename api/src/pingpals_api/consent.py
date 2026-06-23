"""Per-channel consent ledger + fail-closed enforcement (issue 045, FR-6.2, PRIV-1.2/1.15).

Per-channel delivery authorization is derived SOLELY from the latest immutable consent record for
that channel at the relevant instant. Absent consent, an integrity-failed record, or an
indeterminate state all FAIL CLOSED (no delivery on that channel) and the denial is auditable. The
durable append-only persistence of these events is the privacy tier (issue 056); this module owns
the derivation + enforcement semantics the engine and delivery worker rely on.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .audit.sink import AuditEvent, AuditSink


class ConsentState(str, Enum):
    GRANTED = "granted"
    DENIED = "denied"
    INDETERMINATE = "indeterminate"  # integrity/ambiguity -> treated as no-delivery


@dataclass(frozen=True)
class ConsentEvent:
    owner_id: str
    channel: str
    action: str            # "grant" | "withdraw"
    record_time: int       # server-authoritative
    notice_version: str
    seq: int
    integrity_ok: bool = True


class ConsentLedger(Protocol):
    def effective_state(self, owner_id: str, channel: str, at_time: int) -> ConsentState: ...


class InMemoryConsentLedger(ConsentLedger):
    """Append-only ledger; effective state = latest immutable record at or before ``at_time``."""

    def __init__(self) -> None:
        self._events: list[ConsentEvent] = []

    def append(self, event: ConsentEvent) -> None:
        self._events.append(event)  # immutable once written (privacy tier enforces persistence)

    def effective_state(self, owner_id: str, channel: str, at_time: int) -> ConsentState:
        relevant = [
            e for e in self._events
            if e.owner_id == owner_id and e.channel == channel and e.record_time <= at_time
        ]
        if not relevant:
            return ConsentState.DENIED  # no record -> default deny (PRIV-1.2)
        latest = max(relevant, key=lambda e: (e.record_time, e.seq))
        if not latest.integrity_ok:
            return ConsentState.INDETERMINATE  # integrity failed -> no delivery (PRIV-1.15)
        return ConsentState.GRANTED if latest.action == "grant" else ConsentState.DENIED


def is_delivery_consented(
    ledger: ConsentLedger,
    owner_id: str,
    channel: str,
    at_time: int,
    audit: AuditSink | None = None,
) -> bool:
    """True only if the latest immutable record is an active grant; else fail closed + audit."""
    state = ledger.effective_state(owner_id, channel, at_time)
    if state is ConsentState.GRANTED:
        return True
    if audit is not None:
        audit.record(AuditEvent("consent.denied", owner_id, channel, "denied", state.value))
    return False
