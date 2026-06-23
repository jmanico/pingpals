"""Delivery worker: per-reminder owner re-verify + endpoint-ownership + consent (issues 046/053).

At send time the worker, scoped to the reminder's owning user, re-verifies that the chosen channel,
the resolved endpoint, and live channel consent all belong to that same user, and that the payload
is confidentiality-safe. Any mismatch, indeterminate ownership, withdrawn consent, or transient
resolution failure FAILS CLOSED: the reminder is dropped/dead-lettered, never delivered, and the
denial is written to the tamper-evident audit log. A reminder lacking an owning-user attribute is
dead-lettered (the scheduler's cross-user scope is not available here). Each attempt produces a
delivery audit event; if that event cannot be recorded the reminder is treated as not-delivered.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from ..audit.log import TamperEvidentAuditLog
from ..consent import ConsentLedger, is_delivery_consented
from .endpoints import EndpointRegistry
from .payload import ChannelSurface, PayloadError, build_payload
from .retry import CircuitBreaker, DeadLetterQueue


class Outcome(str, Enum):
    DELIVERED = "delivered"
    DROPPED = "dropped"
    SKIPPED = "skipped"
    DEAD_LETTERED = "dead_lettered"


@dataclass(frozen=True)
class ReminderJob:
    owner_id: str | None        # None = schema-violating (must be dead-lettered)
    reminder_id: str
    channel: str
    surface: ChannelSurface
    display_name: str
    outreach_action: str
    can_encrypt_message: bool = False


class DeliveryWorker:
    def __init__(
        self,
        audit: TamperEvidentAuditLog,
        consent: ConsentLedger,
        endpoints: EndpointRegistry,
        send: Callable[[object, object], None],
        breaker: CircuitBreaker | None = None,
        dlq: DeadLetterQueue | None = None,
        now: Callable[[], int] | None = None,
    ) -> None:
        self._audit = audit
        self._consent = consent
        self._endpoints = endpoints
        self._send = send
        self._breaker = breaker or CircuitBreaker()
        self._dlq = dlq or DeadLetterQueue()
        self._now = now or (lambda: 0)

    def process(self, job: ReminderJob) -> Outcome:
        if not job.owner_id:
            self._dead_letter(job, "no_owner")  # AC-04: never look up an owner
            return Outcome.DEAD_LETTERED

        try:
            endpoint = self._endpoints.eligible(job.owner_id, job.channel)
            now = self._now()
            consented = is_delivery_consented(self._consent, job.owner_id, job.channel, now)
        except Exception:
            # Transient resolution failure (store timeout) -> fail closed, never deliver (AC-05).
            self._audit_denial(job, "resolution_error")
            return Outcome.DROPPED

        if endpoint is None or not self._endpoints.owns(job.owner_id, endpoint.id):
            self._audit_denial(job, "endpoint_ownership")  # AC-02 / 037
            return Outcome.DROPPED
        if not consented:
            self._audit_denial(job, "consent_withdrawn")  # AC-03
            return Outcome.DROPPED
        if not self._breaker.allow(job.channel):
            return Outcome.SKIPPED  # breaker open (issue 052 AC-03)

        try:
            payload = build_payload(
                job.reminder_id, job.channel, job.surface, job.display_name, job.outreach_action,
                can_encrypt_message=job.can_encrypt_message,
            )
        except PayloadError:
            self._audit_denial(job, "payload_unencryptable")  # AC-07 push fails closed
            return Outcome.DROPPED

        try:
            self._send(endpoint, payload)
        except Exception:
            self._breaker.record_failure(job.channel)
            self._record_delivery(job, "failed")
            self._dead_letter(job, "send_failed")
            return Outcome.DEAD_LETTERED

        self._breaker.record_success(job.channel)
        # Fail closed on the audit write: if it can't be recorded, treat as not-delivered (042).
        try:
            self._record_delivery(job, "delivered")
        except Exception:
            self._dead_letter(job, "audit_unrecordable")
            return Outcome.DEAD_LETTERED
        return Outcome.DELIVERED

    def _record_delivery(self, job: ReminderJob, outcome: str) -> None:
        # Server time; no message content or PII beyond the minimal ref (042 AC-04/AC-05).
        self._audit.append(
            "delivery.attempt", principal=job.owner_id or "unknown",
            object_ref=f"reminder:{job.reminder_id}|channel:{job.channel}|consent:granted|{outcome}",
        )

    def _audit_denial(self, job: ReminderJob, reason: str) -> None:
        self._audit.append("delivery.denied", principal=job.owner_id or "unknown",
                           object_ref=f"reminder:{job.reminder_id}|{reason}")

    def _dead_letter(self, job: ReminderJob, reason: str) -> None:
        self._audit.append("delivery.dead_letter", principal=job.owner_id or "unknown",
                           object_ref=f"reminder:{job.reminder_id}|{reason}")
        self._dlq.add({"reminder_id": job.reminder_id, "reason": reason})
