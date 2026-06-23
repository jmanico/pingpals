"""Last-contact event logging + cadence-clock reset (issue 039, FR-4.1/4.2, SEC-8.1/8.3).

Logging a contact event resets the contact's cadence clock. The immutable RECORD time is always
server-authoritative; a user-asserted event time is preserved in a SEPARATE field; a
client-supplied "record time" is never accepted (no mass-assignment of the authoritative
timestamp). If the time source is unavailable the record is rejected. A tamper-evident audit entry
is written in the same commit; cross-user logging returns not-found.
"""

from __future__ import annotations

import uuid

from ..audit.log import TamperEvidentAuditLog
from ..persistence.repository import Repository
from ..validation import Field, validate

# Only an optional user-asserted time is accepted; record_time/unknown fields are rejected (AC-05).
_LOG_SCHEMA = {"asserted_time": Field("int", required=False, min_value=0, max_value=4_102_444_800)}


class LastContactError(Exception):
    """Logging failed (fail closed; no write)."""


class LastContactService:
    def __init__(self, repo: Repository, audit: TamperEvidentAuditLog) -> None:
        self._repo = repo
        self._audit = audit

    def log_event(self, owner_id: str, contact_id: str, payload: dict | None = None) -> dict:
        data = validate(_LOG_SCHEMA, payload or {})  # rejects client record_time / unknowns (AC-05)
        contact = self._repo.get(owner_id, "contact", contact_id)
        if contact is None:
            raise LastContactError("contact not found")  # cross-user/missing (AC-06)

        # Server-authoritative record time via the audit append; raises if time unavailable (AC-03).
        entry = self._audit.append("contact.logged", principal=owner_id,
                                   object_ref=f"contact:{contact_id}",
                                   asserted_time=data.get("asserted_time"))
        record_time = entry.record_time

        event_id = uuid.uuid4().hex
        event = self._repo.add(owner_id, "contact_event", event_id, {
            "contact_id": contact_id,
            "record_time": record_time,                 # immutable, server (AC-02)
            "asserted_time": data.get("asserted_time"),  # separate field (AC-02)
        })
        # Reset the cadence clock to the server record time (FR-4.2, AC-01).
        self._repo.update(owner_id, "contact", contact_id, {"last_contacted_at": record_time})
        return event
