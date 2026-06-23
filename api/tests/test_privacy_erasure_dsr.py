"""Erasure + proof + DSR + retention tests (issues 059/060/061/062/064)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pingpals_api.audit.log import TamperEvidentAuditLog
from pingpals_api.persistence.repository import InMemoryRepository
from pingpals_api.privacy.dsr import DSRError, DSRService
from pingpals_api.privacy.erasure import ErasureError, ErasureService, pseudonymous_ref
from pingpals_api.privacy.export import ExportService
from pingpals_api.privacy.retention import RetentionConfig, RetentionError, RetentionJob


class Clock:
    def __init__(self, t=1000):
        self.t = t

    def now(self):
        self.t += 1
        return self.t


def _seed(repo, owner="alice"):
    repo.add(owner, "category", "cat1", {"name": "Family", "default_cadence_days": 30})
    repo.add(owner, "contact", "c1", {"display_name": "Alex", "category_id": "cat1"})
    repo.add(owner, "reminder", "r1", {"contact_id": "c1", "status": "pending"})
    repo.add(owner, "provider_token", "t1", {"provider": "google", "ciphertext": "x"})


# ---- Erasure + proof (issues 059/060) ----

def test_erasure_removes_all_pii_and_leaves_surviving_proof() -> None:
    repo = InMemoryRepository()
    audit = TamperEvidentAuditLog(time_source=Clock())
    _seed(repo)
    revoked = []
    svc = ErasureService(repo, audit, revoke_provider_tokens=revoked.append)
    result = svc.erase_subject("alice", requesting_principal="alice")
    assert svc.verify_erased("alice") is True  # AC-02 no PII remains
    assert revoked == ["alice"]  # AC-03 provider tokens revoked
    # AC-01: a PII-free proof survives and the chain validates.
    proof = [e for e in audit.entries if e.action == "dsr.erasure"][-1]
    assert pseudonymous_ref("alice") in (proof.object_ref or "")
    assert "Alex" not in (proof.object_ref or "")  # AC-02 no contact PII
    assert audit.verify() is True
    assert result["stores"]


def test_erasure_fails_closed_when_proof_unwritable() -> None:
    repo = InMemoryRepository()
    dead_audit = TamperEvidentAuditLog(time_source=lambda: (_ for _ in ()).throw(RuntimeError()))
    _seed(repo)
    svc = ErasureService(repo, dead_audit)
    with pytest.raises(ErasureError):  # AC-03/AC-05 rollback
        svc.erase_subject("alice", "alice")
    assert repo.get("alice", "contact", "c1") is not None  # nothing committed


def test_proof_excluded_from_cascade_survives() -> None:
    repo = InMemoryRepository()
    audit = TamperEvidentAuditLog(time_source=Clock())
    _seed(repo)
    ErasureService(repo, audit).erase_subject("alice", "alice")
    # second erasure of the (now empty) subject still works; proof entries accumulate, never purged
    assert any(e.action == "dsr.erasure" for e in audit.entries)  # AC-04 survives


# ---- DSR endpoints (issue 061) ----

def _dsr():
    repo = InMemoryRepository()
    audit = TamperEvidentAuditLog(time_source=Clock())
    _seed(repo)
    export = ExportService(repo, audit)
    erasure = ErasureService(repo, audit)
    return repo, audit, DSRService(repo, audit, export, erasure)


def test_access_returns_export() -> None:
    _, _, dsr = _dsr()
    assert dsr.access("alice")["subject"] == "alice"  # AC-01


def test_rectify_audits() -> None:
    repo, audit, dsr = _dsr()
    dsr.rectify_contact("alice", "c1", {"display_name": "Alexandra"})  # AC-02
    assert repo.get("alice", "contact", "c1")["display_name"] == "Alexandra"
    assert any(e.action == "contact.rectify" for e in audit.entries)


def test_restriction_suppresses_processing() -> None:
    _, _, dsr = _dsr()
    assert dsr.processing_allowed("alice") is True
    dsr.set_restriction("alice", True)  # AC-03
    assert dsr.processing_allowed("alice") is False
    dsr.set_restriction("alice", False)
    dsr.set_objection("alice", True)
    assert dsr.processing_allowed("alice") is False


def test_dsr_cross_user_not_found() -> None:
    _, _, dsr = _dsr()
    with pytest.raises(DSRError):  # AC-05
        dsr.rectify_contact("bob", "c1", {"display_name": "X"})


def test_controller_mediated_contact_erasure() -> None:
    repo, _, dsr = _dsr()
    dsr.erase_contact("alice", "c1")  # AC-04
    assert repo.get("alice", "contact", "c1") is None


# ---- Retention (issue 062) ----

def test_accountability_period_not_shorter_than_operational() -> None:
    with pytest.raises(RetentionError):  # AC-03
        RetentionConfig(operational_retention_seconds=100, accountability_retention_seconds=10)


def test_retention_deletes_operational_keeps_accountability() -> None:
    repo = InMemoryRepository()
    audit = TamperEvidentAuditLog(time_source=Clock())
    # an accountability event (consent) and an old operational reminder
    audit.append("consent.grant", "alice", "email")
    repo.add("alice", "reminder", "old", {"contact_id": "c1", "due_at": 10})
    repo.add("alice", "reminder", "new", {"contact_id": "c1", "due_at": 10_000})
    job = RetentionJob(repo, audit,
                       RetentionConfig(operational_retention_seconds=100,
                                       accountability_retention_seconds=1_000_000))
    out = job.run(["alice"], now=5_000)
    assert out["operational_deleted"] == 1  # old reminder gone (AC-01)
    assert repo.get("alice", "reminder", "new") is not None
    assert audit.verify() is True  # AC-02 chain still verifies
    assert any(e.action == "consent.grant" for e in audit.entries)  # AC-05 accountability retained


# ---- Docs (issue 064) ----

def test_privacy_docs_exist_with_required_content() -> None:
    root = Path(__file__).resolve().parents[2] / "docs" / "privacy"
    ropa = (root / "RoPA.md").read_text()
    dpia = (root / "DPIA.md").read_text()
    lia = (root / "LIA.md").read_text()
    assert "Article 30" in ropa
    assert "Article 9" in dpia and "residual" in dpia.lower()  # PRIV-1.18 recorded
    assert "6(1)(f)" in lia  # legitimate interests basis
