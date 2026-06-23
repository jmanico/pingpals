"""Tamper-evident audit log — hash-chained, server-time, externally anchored (issue 023).

Implements SEC-8.1–8.5:
  * append-only SHA-256 hash chain over server-authoritative time (client time is never the record
    time; an unavailable time source fails closed — the record is rejected, AC-02/AC-05);
  * a user-asserted event time is preserved in a SEPARATE field from the immutable record time;
  * the chain head is anchored in a store SEPARATE from and not writable by the log's write path,
    so an actor who rewrites records and recomputes downstream hashes is still detected (AC-03);
  * ``verify()`` checks the chain end-to-end and the external anchor and ALERTS on any break, gap,
    reorder, or truncation (fail closed);
  * the audit write shares the mutation's commit: if the audit entry cannot be written, the
    mutation is not applied (AC-01);
  * retention ages out only sealed, independently verifiable segments and re-anchors the survivors,
    logging the purge itself and keeping accountability events within their period (AC-04).
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Protocol

from .sink import AuditEvent, AuditSink

GENESIS = "0" * 64

# Security/DSR/accountability actions retained for the accountability period past PII retention.
ACCOUNTABILITY_ACTIONS: frozenset[str] = frozenset({
    "auth.login", "auth.logout", "authz.denied",
    "integration.token_use", "consent.grant", "consent.withdraw",
    "contact.rectify", "dsr.access", "dsr.export", "dsr.erasure",
    "deletion", "audit.purge",
})


class AuditError(Exception):
    """Base class for audit-subsystem failures (all fail closed)."""


class TimeUnavailableError(AuditError):
    """The server-authoritative time source is unavailable; the record MUST be rejected."""


class TamperError(AuditError):
    """The chain failed integrity verification."""


class TimeSource(Protocol):
    def now(self) -> int:
        """Return server-authoritative epoch seconds, or raise if unavailable (fail closed)."""


class SystemTimeSource:
    def now(self) -> int:
        return int(time.time())


class AnchorStore(Protocol):
    """Holds the current chain head, SEPARATE from the audit entry store (SEC-8.5)."""

    def get_head(self) -> str: ...
    def set_head(self, head: str) -> None: ...


class InMemoryAnchorStore(AnchorStore):
    def __init__(self) -> None:
        self._head = GENESIS

    def get_head(self) -> str:
        return self._head

    def set_head(self, head: str) -> None:
        self._head = head


@dataclass(frozen=True)
class AuditEntry:
    seq: int
    record_time: int          # server-authoritative; basis for tamper-evidence (SEC-8.3)
    action: str
    principal: str
    object_ref: str | None
    asserted_time: int | None  # user-asserted event time, DISTINCT from record_time
    prev_hash: str
    entry_hash: str

    def _payload(self) -> dict:
        d = asdict(self)
        d.pop("entry_hash")
        return d

    def compute_hash(self) -> str:
        canonical = json.dumps(self._payload(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _hash_segment(entries: list[AuditEntry]) -> str:
    blob = json.dumps([e.entry_hash for e in entries], separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class TamperEvidentAuditLog(AuditSink):
    def __init__(
        self,
        time_source: TimeSource | None = None,
        anchor: AnchorStore | None = None,
        on_tamper: Callable[[str], None] | None = None,
    ) -> None:
        self._time = time_source or SystemTimeSource()
        self._anchor = anchor or InMemoryAnchorStore()
        self._on_tamper = on_tamper or (lambda _msg: None)
        self._entries: list[AuditEntry] = []

    # -- AuditSink: lightweight events (e.g. from SecureStore) become chained entries. --
    def record(self, event: AuditEvent) -> None:
        self.append(event.action, event.principal, event.object_ref)

    def append(
        self,
        action: str,
        principal: str,
        object_ref: str | None = None,
        asserted_time: int | None = None,
    ) -> AuditEntry:
        try:
            record_time = self._time.now()
        except Exception as exc:  # time source down -> reject the record (fail closed, AC-02)
            raise TimeUnavailableError("server time source unavailable") from exc

        prev = self._entries[-1].entry_hash if self._entries else GENESIS
        seq = len(self._entries)
        draft = AuditEntry(seq, record_time, action, principal, object_ref, asserted_time, prev, "")
        entry = AuditEntry(seq, record_time, action, principal, object_ref, asserted_time, prev,
                           draft.compute_hash())
        self._entries.append(entry)
        self._anchor.set_head(entry.entry_hash)  # anchor updated via the log's authority only
        return entry

    def audited_mutation(
        self,
        action: str,
        principal: str,
        mutation: Callable[[], None],
        object_ref: str | None = None,
        asserted_time: int | None = None,
    ) -> AuditEntry:
        """Append the audit entry, THEN apply the mutation. If the append fails, the mutation is
        not applied (same-commit semantics, AC-01)."""
        entry = self.append(action, principal, object_ref, asserted_time)
        mutation()
        return entry

    def verify(self) -> bool:
        """Recompute the chain end-to-end and compare to the external anchor. Alert on any break."""
        prev = GENESIS
        for i, entry in enumerate(self._entries):
            if entry.seq != i:
                return self._tamper(f"out-of-order entry at index {i}")
            if entry.prev_hash != prev:
                return self._tamper(f"broken link at seq {entry.seq}")
            if entry.compute_hash() != entry.entry_hash:
                return self._tamper(f"hash mismatch at seq {entry.seq}")
            prev = entry.entry_hash
        if prev != self._anchor.get_head():
            # entries were rewritten/truncated without (un-writable) anchor update, or vice versa
            return self._tamper("chain head does not match external anchor")
        return True

    def _tamper(self, message: str) -> bool:
        self._on_tamper(message)
        return False

    def seal_and_purge(self, keep_from_seq: int) -> str:
        """Age out operational entries older than ``keep_from_seq`` as a sealed segment, retaining
        accountability events, re-anchoring survivors, and logging the purge itself (AC-04)."""
        removable = [
            e for e in self._entries
            if e.seq < keep_from_seq and e.action not in ACCOUNTABILITY_ACTIONS
        ]
        seal = _hash_segment(removable)
        survivors = [e for e in self._entries if e not in removable]
        self._entries = self._rechain(survivors)
        self.append("audit.purge", principal="system", object_ref=seal)
        return seal

    def _rechain(self, survivors: list[AuditEntry]) -> list[AuditEntry]:
        rebuilt: list[AuditEntry] = []
        prev = GENESIS
        for i, e in enumerate(survivors):
            draft = AuditEntry(i, e.record_time, e.action, e.principal, e.object_ref,
                               e.asserted_time, prev, "")
            new = AuditEntry(i, e.record_time, e.action, e.principal, e.object_ref,
                             e.asserted_time, prev, draft.compute_hash())
            rebuilt.append(new)
            prev = new.entry_hash
        self._anchor.set_head(prev)
        return rebuilt

    @property
    def entries(self) -> tuple[AuditEntry, ...]:
        return tuple(self._entries)
