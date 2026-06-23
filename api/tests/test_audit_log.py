"""Tamper-evident audit log tests (issue 023 / REQ-FND-012)."""

from __future__ import annotations

import dataclasses

import pytest

from pingpals_api.audit.log import (
    InMemoryAnchorStore,
    TamperEvidentAuditLog,
    TimeUnavailableError,
)


class FixedTime:
    def __init__(self, value: int = 1_000) -> None:
        self.value = value

    def now(self) -> int:
        self.value += 1
        return self.value


class DeadTime:
    def now(self) -> int:
        raise RuntimeError("ntp unreachable")


def _log(on_tamper=None) -> TamperEvidentAuditLog:
    return TamperEvidentAuditLog(time_source=FixedTime(), anchor=InMemoryAnchorStore(),
                                 on_tamper=on_tamper)


def test_consent_grant_then_withdraw_two_ordered_attributable_entries() -> None:
    log = _log()
    log.append("consent.grant", principal="user-A", object_ref="email")
    log.append("consent.withdraw", principal="user-A", object_ref="email")
    entries = log.entries
    assert [e.action for e in entries] == ["consent.grant", "consent.withdraw"]  # AC-01
    assert [e.seq for e in entries] == [0, 1]
    assert all(e.principal == "user-A" for e in entries)
    assert log.verify() is True


def test_same_commit_audit_failure_blocks_mutation() -> None:
    # AC-01: if the audit write fails (time source down), the mutation is not applied.
    log = TamperEvidentAuditLog(time_source=DeadTime())
    applied = {"v": False}

    def mutation() -> None:
        applied["v"] = True

    with pytest.raises(TimeUnavailableError):
        log.audited_mutation("deletion", "user-A", mutation, object_ref="contact-1")
    assert applied["v"] is False


def test_server_time_is_record_time_asserted_time_separate() -> None:
    # AC-02 / AC-05: record_time is server-authoritative; user-asserted time is a separate field.
    log = _log()
    entry = log.append("contact.rectify", "user-A", object_ref="c1", asserted_time=1)
    assert entry.record_time > 900  # from the server clock, not the asserted "1"
    assert entry.asserted_time == 1
    assert entry.record_time != entry.asserted_time


def test_unavailable_time_source_rejects_record() -> None:
    log = TamperEvidentAuditLog(time_source=DeadTime())
    with pytest.raises(TimeUnavailableError):  # AC-02 fail closed
        log.append("auth.login", "user-A")


def test_tamper_with_history_is_detected_and_alerts() -> None:
    alerts: list[str] = []
    log = _log(on_tamper=alerts.append)
    for i in range(4):
        log.append("integration.token_use", "user-A", object_ref=f"t{i}")
    assert log.verify() is True

    # Attacker rewrites a historical entry's content WITHOUT access to the external anchor.
    tampered = dataclasses.replace(log._entries[1], object_ref="forged")
    log._entries[1] = tampered  # naive mutation: stored hash no longer matches content
    assert log.verify() is False  # AC-03
    assert alerts


def test_tail_truncation_detected_via_anchor() -> None:
    alerts: list[str] = []
    log = _log(on_tamper=alerts.append)
    for i in range(3):
        log.append("auth.login", "user-A", object_ref=f"s{i}")
    # Remove the last entry but DON'T touch the (un-writable) anchor.
    log._entries.pop()
    assert log.verify() is False  # recomputed head != anchored head
    assert alerts


def test_reorder_detected() -> None:
    alerts: list[str] = []
    log = _log(on_tamper=alerts.append)
    for i in range(3):
        log.append("dsr.access", "user-A", object_ref=f"r{i}")
    log._entries[0], log._entries[1] = log._entries[1], log._entries[0]
    assert log.verify() is False
    assert alerts


def test_retention_purge_seals_reanchors_and_keeps_accountability() -> None:
    log = _log()
    # Mix operational (crypto.decrypt) and accountability (consent.grant) history.
    log.append("crypto.decrypt", "google-adapter", object_ref="t0")   # seq 0 operational
    log.append("crypto.decrypt", "google-adapter", object_ref="t1")   # seq 1 operational
    log.append("consent.grant", "user-A", object_ref="email")          # seq 2 accountability
    log.append("crypto.decrypt", "google-adapter", object_ref="t3")   # seq 3 operational

    log.seal_and_purge(keep_from_seq=3)  # age out operational entries older than seq 3

    actions = [e.action for e in log.entries]
    # AC-04: operational seqs 0-1 gone; accountability consent.grant retained; purge logged.
    assert actions.count("crypto.decrypt") == 1  # only the seq-3 one survives the cutoff
    assert "consent.grant" in actions            # accountability event retained
    assert actions[-1] == "audit.purge"          # the purge is itself a tamper-evident entry
    assert log.verify() is True                  # surviving chain re-anchored and verifies
