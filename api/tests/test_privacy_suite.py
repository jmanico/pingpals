"""Privacy test suite (issue 078, TEST-1.4).

Consolidated coverage of: erasure cascade (PRIV-1.6), export completeness (PRIV-1.5), consent
fail-closed delivery (FR-6.2), and retention expiry (PRIV-1.9).
"""

from __future__ import annotations

from pingpals_api.audit.log import TamperEvidentAuditLog
from pingpals_api.consent import ConsentEvent, InMemoryConsentLedger, is_delivery_consented
from pingpals_api.persistence.repository import InMemoryRepository
from pingpals_api.privacy.erasure import ErasureService
from pingpals_api.privacy.export import ExportService
from pingpals_api.privacy.retention import RetentionConfig, RetentionJob


class Clock:
    def __init__(self, t=1000):
        self.t = t

    def now(self):
        self.t += 1
        return self.t


def _seed(repo, owner="alice"):
    repo.add(owner, "category", "cat1", {"name": "Family", "default_cadence_days": 30})
    repo.add(owner, "contact", "c1", {"display_name": "Alex", "category_id": "cat1"})
    repo.add(owner, "reminder", "r1", {"contact_id": "c1", "due_at": 10})


def test_erasure_cascade_leaves_no_pii() -> None:  # PRIV-1.6
    repo = InMemoryRepository()
    audit = TamperEvidentAuditLog(time_source=Clock())
    _seed(repo)
    svc = ErasureService(repo, audit)
    svc.erase_subject("alice", "alice")
    assert svc.verify_erased("alice") is True
    assert audit.verify() is True  # proof survives, chain validates


def test_export_completeness_and_isolation() -> None:  # PRIV-1.5 / SEC-2.2
    repo = InMemoryRepository()
    _seed(repo)
    repo.add("bob", "contact", "c2", {"display_name": "Bob", "category_id": "x"})
    export = ExportService(repo, TamperEvidentAuditLog(time_source=Clock())).build_export("alice")
    assert [c["display_name"] for c in export["data"]["contact"]] == ["Alex"]
    assert export["data"]["reminder"]  # history included


def test_consent_fail_closed_delivery() -> None:  # FR-6.2
    led = InMemoryConsentLedger()
    assert is_delivery_consented(led, "alice", "email", 100) is False  # no record -> no delivery
    led.append(ConsentEvent("alice", "email", "grant", 1, "v1", 0))
    assert is_delivery_consented(led, "alice", "email", 100) is True
    led.append(ConsentEvent("alice", "email", "withdraw", 50, "v1", 1))
    assert is_delivery_consented(led, "alice", "email", 100) is False  # withdrawn -> fail closed


def test_retention_expiry_deletes_old_records() -> None:  # PRIV-1.9
    repo = InMemoryRepository()
    audit = TamperEvidentAuditLog(time_source=Clock())
    repo.add("alice", "reminder", "old", {"contact_id": "c1", "due_at": 10})
    repo.add("alice", "reminder", "new", {"contact_id": "c1", "due_at": 9_000})
    job = RetentionJob(repo, audit,
                       RetentionConfig(operational_retention_seconds=100,
                                       accountability_retention_seconds=1_000_000))
    out = job.run(["alice"], now=5_000)
    assert out["operational_deleted"] == 1
    assert repo.get("alice", "reminder", "old") is None
    assert repo.get("alice", "reminder", "new") is not None
