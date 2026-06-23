"""Consent store + export + export access + privacy defaults tests (issues 056/057/058/063)."""

from __future__ import annotations

import json

import pytest

from pingpals_api.audit.log import TamperEvidentAuditLog
from pingpals_api.consent import ConsentState, is_delivery_consented
from pingpals_api.persistence.repository import InMemoryRepository
from pingpals_api.privacy.consent_store import ConsentStore
from pingpals_api.privacy.defaults import (
    NOTES_ENTRY_NOTICE,
    NotesProcessingError,
    default_privacy_settings,
    guard_notes_not_processed,
    is_most_restrictive,
)
from pingpals_api.privacy.export import ExportService
from pingpals_api.privacy.export_access import ExportAccessDenied, ExportArtifactStore


class Clock:
    def __init__(self, t=1000):
        self.t = t

    def now(self):
        self.t += 1
        return self.t


# ---- Consent store (issue 056) ----

def test_grant_then_withdraw_two_distinct_audited_events() -> None:
    audit = TamperEvidentAuditLog(time_source=Clock())
    store = ConsentStore(audit)
    store.grant("alice", "email", "v1")
    store.withdraw("alice", "email", "v1")
    hist = store.history("alice")
    assert [e.action for e in hist] == ["grant", "withdraw"]  # AC-01 distinct ordered
    assert sum(1 for e in audit.entries if e.action.startswith("consent.")) == 2


def test_delivery_authorized_only_from_latest_record() -> None:
    audit = TamperEvidentAuditLog(time_source=Clock())
    store = ConsentStore(audit)
    g = store.grant("alice", "email", "v1")
    assert store.effective_state("alice", "email", g.record_time + 1) is ConsentState.GRANTED
    w = store.withdraw("alice", "email", "v1")
    after = w.record_time + 1
    assert store.effective_state("alice", "email", after) is ConsentState.DENIED  # AC-03
    assert is_delivery_consented(store.ledger, "alice", "email", w.record_time + 1) is False


# ---- Export (issue 057) ----

def _repo_with_data():
    repo = InMemoryRepository()
    repo.add("alice", "category", "cat1", {"name": "Family", "default_cadence_days": 30})
    repo.add("alice", "contact", "c1", {"display_name": "Alex", "category_id": "cat1"})
    repo.add("bob", "contact", "c2", {"display_name": "Bob's", "category_id": "x"})
    return repo


def test_export_is_complete_and_user_scoped() -> None:
    repo = _repo_with_data()
    audit = TamperEvidentAuditLog(time_source=Clock())
    artifact = ExportService(repo, audit).build_export("alice")
    assert artifact["subject"] == "alice"
    names = [c["display_name"] for c in artifact["data"]["contact"]]
    assert names == ["Alex"]  # AC-01/AC-02
    assert "Bob's" not in json.dumps(artifact)  # AC-05 no cross-user data
    assert any(e.action == "dsr.export" for e in audit.entries)  # AC-03


def test_export_json_round_trips() -> None:
    repo = _repo_with_data()
    raw = ExportService(repo, TamperEvidentAuditLog(time_source=Clock())).to_json("alice")
    parsed = json.loads(raw)
    assert parsed["data"]["contact"][0]["display_name"] == "Alex"


# ---- Export access control (issue 058) ----

def test_download_requires_owner_token_single_use() -> None:
    store = ExportArtifactStore(ttl_seconds=900, now=Clock(1000).now)
    aid, token = store.put("alice", b"payload")
    assert store.download(aid, "alice", token) == b"payload"  # AC-01
    with pytest.raises(ExportAccessDenied):  # AC-04 single-use
        store.download(aid, "alice", token)


def test_download_denied_for_non_owner_and_bad_token() -> None:
    store = ExportArtifactStore(now=Clock(1000).now)
    aid, token = store.put("alice", b"payload")
    with pytest.raises(ExportAccessDenied):  # AC-05 non-owner -> not found
        store.download(aid, "bob", token)
    with pytest.raises(ExportAccessDenied):
        store.download(aid, "alice", "wrong-token")


def test_download_expires() -> None:
    clock = Clock(1000)
    store = ExportArtifactStore(ttl_seconds=10, now=clock.now)
    aid, token = store.put("alice", b"payload")
    clock.t += 100
    with pytest.raises(ExportAccessDenied):  # AC-04 expiry
        store.download(aid, "alice", token)


def test_purge_for_owner_on_erasure() -> None:
    store = ExportArtifactStore(now=Clock(1000).now)
    store.put("alice", b"x")
    store.put("alice", b"y")
    assert store.purge_for_owner("alice") == 2  # AC-02


# ---- Privacy defaults + notes guard (issue 063) ----

def test_defaults_are_most_restrictive() -> None:
    assert is_most_restrictive(default_privacy_settings()) is True  # PRIV-1.13


def test_notes_entry_notice_present_and_display_only() -> None:
    assert "special-category" in NOTES_ENTRY_NOTICE
    guard_notes_not_processed("display")  # ok
    with pytest.raises(NotesProcessingError):  # PRIV-1.18 notes never a processing input
        guard_notes_not_processed("index")
