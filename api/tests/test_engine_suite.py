"""Reminder-engine test suite (issue 079, TEST-1.5).

Consolidated coverage of: idempotency (FR-5.2), cadence boundary conditions, and quiet-hours /
timezone fail-closed (FR-3.3).
"""

from __future__ import annotations

import calendar
from datetime import UTC, datetime

from pingpals_api.audit.log import TamperEvidentAuditLog
from pingpals_api.consent import ConsentEvent, InMemoryConsentLedger
from pingpals_api.contacts.cadence import is_delivery_allowed
from pingpals_api.persistence.repository import InMemoryRepository
from pingpals_api.scheduler.engine import Scheduler, UserSettings

DAY = 86_400


class Clock:
    def __init__(self, t=10_000_000):
        self.t = t

    def now(self):
        self.t += 1
        return self.t


def _epoch(y, mo, d, h, mi):
    return calendar.timegm(datetime(y, mo, d, h, mi, tzinfo=UTC).timetuple())


def _sched(last_contacted, now):
    repo = InMemoryRepository()
    repo.add("alice", "category", "cat1", {"name": "Family", "default_cadence_days": 7})
    repo.add("alice", "contact", "c1",
             {"display_name": "Alex", "category_id": "cat1", "last_contacted_at": last_contacted})
    led = InMemoryConsentLedger()
    led.append(ConsentEvent("alice", "email", "grant", 1, "v1", 0))
    return repo, Scheduler(repo, TamperEvidentAuditLog(time_source=Clock()), led)


def _settings(**o):
    base = {"timezone": "UTC", "quiet_hours": None, "channel": "email", "paused": False,
            "per_window_cap": 50}
    base.update(o)
    return UserSettings(**base)


def test_idempotent_generation() -> None:  # FR-5.2
    now = 10_000_000
    repo, sched = _sched(last_contacted=0, now=now)
    first = sched.evaluate_user("alice", _settings(), now, "w1")
    second = sched.evaluate_user("alice", _settings(), now, "w1")
    assert len(first) == 1 and second == []


def test_cadence_boundary() -> None:
    now = 10_000_000
    cadence = 7 * DAY
    # exactly at the boundary (now - last == cadence) -> due
    repo, sched = _sched(last_contacted=now - cadence, now=now)
    assert len(sched.evaluate_user("alice", _settings(), now, "w1")) == 1
    # one second short -> not due
    repo, sched = _sched(last_contacted=now - cadence + 1, now=now)
    assert sched.evaluate_user("alice", _settings(), now, "w2") == []


def test_quiet_hours_and_timezone_fail_closed() -> None:  # FR-3.3
    now = _epoch(2026, 6, 23, 2, 0)  # 02:00 UTC
    repo, sched = _sched(last_contacted=0, now=now)
    # inside quiet hours -> no reminder
    assert sched.evaluate_user("alice", _settings(quiet_hours=(22 * 60, 7 * 60)), now, "w1") == []
    # unknown timezone -> fail closed
    assert sched.evaluate_user("alice", _settings(timezone="Not/AZone"), now, "w2") == []


def test_quiet_hours_window_helper() -> None:
    quiet = (22 * 60, 7 * 60)
    assert is_delivery_allowed(_epoch(2026, 6, 23, 2, 0), "UTC", quiet) is False
    assert is_delivery_allowed(_epoch(2026, 6, 23, 12, 0), "UTC", quiet) is True
    assert is_delivery_allowed(_epoch(2026, 6, 23, 12, 0), "Bad/Zone", None) is False
