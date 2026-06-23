"""Last-contact logging tests (issue 039 / REQ-CONTACTS-028)."""

from __future__ import annotations

import pytest

from pingpals_api.audit.log import TamperEvidentAuditLog, TimeUnavailableError
from pingpals_api.contacts.last_contact import LastContactError, LastContactService
from pingpals_api.persistence.repository import InMemoryRepository
from pingpals_api.validation import ValidationError


class Clock:
    def __init__(self, t: int = 5000) -> None:
        self.t = t

    def now(self) -> int:
        return self.t


def _setup(clock=None):
    repo = InMemoryRepository()
    audit = TamperEvidentAuditLog(time_source=clock or Clock())
    repo.add("alice", "category", "cat1", {"name": "Family", "default_cadence_days": 30})
    repo.add("alice", "contact", "c1", {"display_name": "Alex", "category_id": "cat1"})
    return repo, audit, LastContactService(repo, audit)


def test_log_resets_cadence_clock_with_audit() -> None:
    repo, audit, svc = _setup(Clock(5000))
    svc.log_event("alice", "c1")  # AC-01
    assert repo.get("alice", "contact", "c1")["last_contacted_at"] == 5000
    assert any(e.action == "contact.logged" for e in audit.entries)  # AC-04


def test_asserted_time_separate_from_server_record_time() -> None:
    repo, _, svc = _setup(Clock(5000))
    event = svc.log_event("alice", "c1", {"asserted_time": 1})  # backdated
    assert event["record_time"] == 5000   # immutable server time (AC-02)
    assert event["asserted_time"] == 1     # preserved separately


def test_client_supplied_record_time_rejected() -> None:
    _, _, svc = _setup()
    with pytest.raises(ValidationError):  # AC-05 no mass-assignment of authoritative time
        svc.log_event("alice", "c1", {"record_time": 1})


def test_time_source_unavailable_rejects() -> None:
    repo = InMemoryRepository()
    audit = TamperEvidentAuditLog(time_source=lambda: (_ for _ in ()).throw(RuntimeError()))
    repo.add("alice", "contact", "c1", {"display_name": "Alex", "category_id": "cat1"})
    svc = LastContactService(repo, audit)
    with pytest.raises(TimeUnavailableError):  # AC-03
        svc.log_event("alice", "c1")
    assert "last_contacted_at" not in (repo.get("alice", "contact", "c1") or {})


def test_cross_user_logging_not_found() -> None:
    _, _, svc = _setup()
    with pytest.raises(LastContactError):  # AC-06
        svc.log_event("bob", "c1")
