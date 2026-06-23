"""Reminder action tests (issue 044 / REQ-ENGINE-033)."""

from __future__ import annotations

import pytest

from pingpals_api.audit.log import TamperEvidentAuditLog
from pingpals_api.contacts.last_contact import LastContactService
from pingpals_api.persistence.repository import InMemoryRepository
from pingpals_api.scheduler.actions import ReminderActionError, ReminderActions


class Clock:
    def __init__(self, t=5000):
        self.t = t

    def now(self):
        return self.t


def _setup():
    repo = InMemoryRepository()
    audit = TamperEvidentAuditLog(time_source=Clock())
    repo.add("alice", "category", "cat1", {"name": "Family", "default_cadence_days": 30})
    repo.add("alice", "contact", "c1", {"display_name": "Alex", "category_id": "cat1"})
    repo.add("alice", "reminder", "r1", {"contact_id": "c1", "status": "pending"})
    actions = ReminderActions(repo, audit, LastContactService(repo, audit))
    return repo, audit, actions


def test_snooze_sets_contact_snooze_and_audits() -> None:
    repo, audit, actions = _setup()
    actions.snooze("alice", "r1", until=9999)  # AC-01
    assert repo.get("alice", "contact", "c1")["snooze_until"] == 9999
    assert repo.get("alice", "reminder", "r1")["status"] == "snoozed"
    assert any(e.action == "reminder.snooze" for e in audit.entries)  # AC-04


def test_dismiss_does_not_reset_clock() -> None:
    repo, _, actions = _setup()
    actions.dismiss("alice", "r1")  # AC-02
    assert repo.get("alice", "reminder", "r1")["status"] == "dismissed"
    assert "last_contacted_at" not in (repo.get("alice", "contact", "c1") or {})


def test_mark_contacted_resets_clock() -> None:
    repo, _, actions = _setup()
    actions.mark_contacted("alice", "r1")  # AC-03
    assert repo.get("alice", "reminder", "r1")["status"] == "contacted"
    assert repo.get("alice", "contact", "c1")["last_contacted_at"] == 5000  # clock reset


def test_cross_user_action_not_found() -> None:
    _, _, actions = _setup()
    for fn in (lambda: actions.dismiss("bob", "r1"),
               lambda: actions.mark_contacted("bob", "r1"),
               lambda: actions.snooze("bob", "r1", 1)):
        with pytest.raises(ReminderActionError):  # AC-05
            fn()
