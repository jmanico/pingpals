"""Reminder actions: snooze / dismiss / mark-contacted (issue 044, FR-5.3/7.2).

Snooze suppresses further generation/delivery for that contact until it expires; dismiss resolves
the reminder WITHOUT resetting the cadence clock; mark-contacted resolves AND resets the clock via
the last-contact logging path (issue 039). Every action writes a tamper-evident audit entry.
Cross-user actions return not-found and change nothing.
"""

from __future__ import annotations

from ..audit.log import TamperEvidentAuditLog
from ..contacts.last_contact import LastContactService
from ..persistence.repository import Repository


class ReminderActionError(Exception):
    """Reminder action failed (fail closed; no state change)."""


class ReminderActions:
    def __init__(
        self,
        repo: Repository,
        audit: TamperEvidentAuditLog,
        last_contact: LastContactService,
    ) -> None:
        self._repo = repo
        self._audit = audit
        self._last_contact = last_contact

    def _owned(self, owner_id: str, reminder_id: str) -> dict:
        reminder = self._repo.get(owner_id, "reminder", reminder_id)
        if reminder is None:
            raise ReminderActionError("reminder not found")  # cross-user/missing (AC-05)
        return reminder

    def snooze(self, owner_id: str, reminder_id: str, until: int) -> dict:
        reminder = self._owned(owner_id, reminder_id)
        self._repo.update(owner_id, "reminder", reminder_id, {"status": "snoozed"})
        # Suppress further generation/delivery for the contact until the snooze expires (AC-01).
        self._repo.update(owner_id, "contact", reminder["contact_id"], {"snooze_until": until})
        self._audit.append("reminder.snooze", principal=owner_id, object_ref=reminder_id)  # AC-04
        return self._repo.get(owner_id, "reminder", reminder_id)

    def dismiss(self, owner_id: str, reminder_id: str) -> dict:
        self._owned(owner_id, reminder_id)
        # Resolve WITHOUT resetting the cadence clock (AC-02).
        self._repo.update(owner_id, "reminder", reminder_id, {"status": "dismissed"})
        self._audit.append("reminder.dismiss", principal=owner_id, object_ref=reminder_id)
        return self._repo.get(owner_id, "reminder", reminder_id)

    def mark_contacted(self, owner_id: str, reminder_id: str) -> dict:
        reminder = self._owned(owner_id, reminder_id)
        # Reset the cadence clock via the last-contact logging path (AC-03, issue 039).
        self._last_contact.log_event(owner_id, reminder["contact_id"])
        self._repo.update(owner_id, "reminder", reminder_id, {"status": "contacted"})
        self._audit.append("reminder.mark_contacted", principal=owner_id, object_ref=reminder_id)
        return self._repo.get(owner_id, "reminder", reminder_id)
