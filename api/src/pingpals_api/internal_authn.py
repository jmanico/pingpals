"""Internal east-west message authentication (issue 027, SECURITY.md §3, SEC-2.1/2.2/2.3).

Zero Trust applies INSIDE the boundary: the Scheduler, Delivery worker, and any queue consumer
must not trust a peer or a work item on network position. Every work item is carried in a signed
envelope (HMAC-SHA256 here; the concrete transport mechanism follows the chosen queue/broker —
DECISION 070 — and stays behind this interface) and is, at the consumer:
  * authenticated to its producer (MAC, constant-time compare),
  * checked for freshness + replay (TTL window + single-use nonce — idempotent, ARCH Rule 8),
  * authorized against its asserted owning user (the producer's enqueue entitlement; the
    Scheduler's cross-user evaluation scope does NOT propagate as delivery authority — FR-5.5).
Any failure FAILS CLOSED: the item is rejected, audited, and dead-lettered — never processed.
This is distinct from external webhook signature verification (SEC-7.1).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import Callable
from dataclasses import dataclass

from .audit.sink import AuditEvent, AuditSink


@dataclass(frozen=True)
class WorkEnvelope:
    producer: str
    owner_id: str
    payload: dict
    nonce: str
    issued_at: int
    mac: str


def _canonical(producer: str, owner_id: str, payload: dict, nonce: str, issued_at: int) -> bytes:
    body = {
        "producer": producer,
        "owner_id": owner_id,
        "payload": payload,
        "nonce": nonce,
        "issued_at": issued_at,
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_mac(key: bytes, producer: str, owner_id: str, payload: dict, nonce: str,
                issued_at: int) -> str:
    return hmac.new(key, _canonical(producer, owner_id, payload, nonce, issued_at),
                    hashlib.sha256).hexdigest()


def sign(key: bytes, producer: str, owner_id: str, payload: dict, nonce: str,
         issued_at: int) -> WorkEnvelope:
    mac = compute_mac(key, producer, owner_id, payload, nonce, issued_at)
    return WorkEnvelope(producer, owner_id, payload, nonce, issued_at, mac)


class MessageRejected(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class WorkItemConsumer:
    """Authenticates, de-duplicates, and authorizes internal work items before processing."""

    def __init__(
        self,
        key: bytes,
        audit: AuditSink,
        dead_letter: Callable[[WorkEnvelope, str], None],
        owner_authorized: Callable[[str, str], bool],
        time_source: Callable[[], int] | None = None,
        ttl_seconds: int = 300,
    ) -> None:
        self._key = key
        self._audit = audit
        self._dead_letter = dead_letter
        self._owner_authorized = owner_authorized
        self._now = time_source or (lambda: int(time.time()))
        self._ttl = ttl_seconds
        self._seen: set[str] = set()

    def consume(self, env: WorkEnvelope, handler: Callable[[dict, str], None]) -> bool:
        """Process the item exactly once if valid; otherwise reject + audit + dead-letter."""
        try:
            self._authenticate(env)
            self._check_freshness(env)
            self._check_replay(env)
            self._authorize(env)
        except MessageRejected as rej:
            self._audit.record(
                AuditEvent("internal.rejected", env.producer, rej.reason, "denied", env.nonce)
            )
            self._dead_letter(env, rej.reason)
            return False  # never processed -> no delivery (AC-01/03/04/05/06)

        self._seen.add(env.nonce)  # mark processed (idempotency / replay defense)
        handler(env.payload, env.owner_id)
        return True

    def _authenticate(self, env: WorkEnvelope) -> None:
        expected = compute_mac(self._key, env.producer, env.owner_id, env.payload, env.nonce,
                               env.issued_at)
        if not hmac.compare_digest(expected, env.mac):
            raise MessageRejected("integrity")  # forged/tampered (AC-03)

    def _check_freshness(self, env: WorkEnvelope) -> None:
        age = self._now() - env.issued_at
        if age < 0 or age > self._ttl:
            raise MessageRejected("stale")  # outside the replay window

    def _check_replay(self, env: WorkEnvelope) -> None:
        if env.nonce in self._seen:
            raise MessageRejected("replay")  # already processed (AC-04)

    def _authorize(self, env: WorkEnvelope) -> None:
        if not self._owner_authorized(env.producer, env.owner_id):
            raise MessageRejected("authz")  # producer not entitled to this owner (AC-05)
