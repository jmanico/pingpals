"""Scheduler cadence-evaluation + generation-cap tests (issues 042/043)."""

from __future__ import annotations

from pingpals_api.audit.log import TamperEvidentAuditLog
from pingpals_api.consent import ConsentEvent, InMemoryConsentLedger
from pingpals_api.persistence.repository import InMemoryRepository
from pingpals_api.scheduler.engine import Scheduler, UserSettings

NOW = 10_000_000  # noon-ish UTC epoch; far from any quiet window we set
WINDOW = "2026-06-23T12"


class Clock:
    def __init__(self, t=NOW):
        self.t = t

    def now(self):
        self.t += 1
        return self.t


def _settings(**over) -> UserSettings:
    base = {"timezone": "UTC", "quiet_hours": None, "channel": "email", "paused": False,
            "per_window_cap": 50}
    base.update(over)
    return UserSettings(**base)


def _setup(consented=True, last_contacted=0, contacts=1):
    repo = InMemoryRepository()
    audit = TamperEvidentAuditLog(time_source=Clock())
    repo.add("alice", "category", "cat1", {"name": "Family", "default_cadence_days": 1})
    for i in range(contacts):
        repo.add("alice", "contact", f"c{i}", {
            "display_name": f"C{i}", "category_id": "cat1", "last_contacted_at": last_contacted,
        })
    led = InMemoryConsentLedger()
    if consented:
        led.append(ConsentEvent("alice", "email", "grant", 1, "v1", 0))
    return repo, audit, led, Scheduler(repo, audit, led)


def test_generates_one_reminder_when_all_conditions_met() -> None:
    repo, _, _, sched = _setup()
    out = sched.evaluate_user("alice", _settings(), NOW, WINDOW)
    assert len(out) == 1  # AC-01
    assert out[0]["channel"] == "email" and out[0]["status"] == "pending"


def test_idempotent_rerun_no_duplicates() -> None:
    repo, _, _, sched = _setup()
    sched.evaluate_user("alice", _settings(), NOW, WINDOW)
    again = sched.evaluate_user("alice", _settings(), NOW, WINDOW)
    assert again == []  # AC-02
    assert len(repo.list("alice", "reminder")) == 1


def test_no_reminder_when_cadence_not_elapsed() -> None:
    _, _, _, sched = _setup(last_contacted=NOW - 10)  # contacted 10s ago, cadence 1 day
    assert sched.evaluate_user("alice", _settings(), NOW, WINDOW) == []  # AC-03


def test_no_reminder_without_consent() -> None:
    _, _, _, sched = _setup(consented=False)
    assert sched.evaluate_user("alice", _settings(), NOW, WINDOW) == []  # AC-03/AC-05


def test_unknown_timezone_fails_closed() -> None:
    _, _, _, sched = _setup()
    assert sched.evaluate_user("alice", _settings(timezone="Not/AZone"), NOW, WINDOW) == []  # AC-05


def test_paused_account_generates_nothing() -> None:
    _, _, _, sched = _setup()
    assert sched.evaluate_user("alice", _settings(paused=True), NOW, WINDOW) == []


def test_active_snooze_suppresses() -> None:
    repo, _, _, sched = _setup()
    repo.update("alice", "contact", "c0", {"snooze_until": NOW + 1000})
    assert sched.evaluate_user("alice", _settings(), NOW, WINDOW) == []  # AC-03


def test_per_window_cap_enforced_and_recorded() -> None:
    repo, audit, _, sched = _setup(contacts=5)
    out = sched.evaluate_user("alice", _settings(per_window_cap=2), NOW, WINDOW)
    assert len(out) == 2  # AC-01/AC-02
    assert any(e.action == "scheduler.cap_reached" for e in audit.entries)  # AC-03


def test_next_window_resets_cap_counter() -> None:
    repo, _, _, sched = _setup(contacts=3)
    first = sched.evaluate_user("alice", _settings(per_window_cap=1), NOW, "w1")
    second = sched.evaluate_user("alice", _settings(per_window_cap=1), NOW, "w2")
    assert len(first) == 1 and len(second) == 1  # AC-04 no permanent starvation
