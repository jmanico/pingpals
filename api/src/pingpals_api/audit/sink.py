"""Audit sink interface + recording reference (issue 022 dependency; full log is issue 023).

Decrypt/unwrap invocations and denials (issue 022) and, later, every security/DSR event are
written here. The tamper-evident, hash-chained, externally-anchored implementation is issue 023;
it will implement this same ``AuditSink`` protocol. Events carry NO plaintext, secrets, or tokens
(SEC-8.2).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class AuditEvent:
    """A single audit record. By construction it holds no plaintext/secret material (SEC-8.2)."""

    action: str            # e.g. "crypto.decrypt", "crypto.decrypt.denied", "authz.denied"
    principal: str         # acting component / user — who
    purpose: str           # data class / purpose / capability — over what
    outcome: str           # "allowed" | "denied"
    object_ref: str | None = None  # opaque reference, never personal data


@runtime_checkable
class AuditSink(Protocol):
    def record(self, event: AuditEvent) -> None:
        """Append ``event`` to the trail. The real sink fails closed if it cannot (issue 023)."""


class RecordingAuditSink(AuditSink):
    """In-memory sink for tests/bootstrap. Replaced by the tamper-evident log (issue 023)."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> None:
        self.events.append(event)
