"""Append-only immutable consent event store (issue 056, PRIV-1.2/1.15, SEC-8.1).

Granting or withdrawing consent appends a NEW immutable event capturing a server-authoritative
timestamp, the channel/scope, and the notice version; existing records are never edited, deleted
(outside erasure), or backdated. Each change is also written as a distinct entry in the
tamper-evident audit trail (issue 023). Per-channel delivery authorization is evaluated ONLY from
the latest immutable record (via the consent ledger); a missing or integrity-failed record yields
no delivery. Consent is settable only through this store — never via a general contact/preferences
write (no mass-assignment).
"""

from __future__ import annotations

from ..audit.log import TamperEvidentAuditLog
from ..consent import ConsentEvent, ConsentState, InMemoryConsentLedger


class ConsentStore:
    def __init__(self, audit: TamperEvidentAuditLog) -> None:
        self._audit = audit
        self._ledger = InMemoryConsentLedger()
        self._seq = 0

    @property
    def ledger(self) -> InMemoryConsentLedger:
        return self._ledger

    def _append(
        self, owner_id: str, channel: str, action: str, notice_version: str
    ) -> ConsentEvent:
        # Server-authoritative time + distinct audit entry, same commit (AC-01).
        entry = self._audit.append(f"consent.{action}", principal=owner_id,
                                   object_ref=f"channel:{channel}|notice:{notice_version}")
        event = ConsentEvent(owner_id, channel, action, entry.record_time, notice_version,
                             self._seq)
        self._seq += 1
        self._ledger.append(event)  # immutable; never edited/backdated (AC-03)
        return event

    def grant(self, owner_id: str, channel: str, notice_version: str) -> ConsentEvent:
        return self._append(owner_id, channel, "grant", notice_version)

    def withdraw(self, owner_id: str, channel: str, notice_version: str) -> ConsentEvent:
        return self._append(owner_id, channel, "withdraw", notice_version)

    def effective_state(self, owner_id: str, channel: str, at_time: int) -> ConsentState:
        return self._ledger.effective_state(owner_id, channel, at_time)

    def history(self, owner_id: str) -> list[ConsentEvent]:
        return [e for e in self._ledger._events if e.owner_id == owner_id]
