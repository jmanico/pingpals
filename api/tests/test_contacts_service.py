"""Contact CRUD + cascade deletion + category + quota tests (issues 035/036/037/040)."""

from __future__ import annotations

import pytest

from pingpals_api.audit.log import TamperEvidentAuditLog, TimeUnavailableError
from pingpals_api.contacts.categories import CategoryError, CategoryService
from pingpals_api.contacts.quotas import QuotaConfig, QuotaExceeded
from pingpals_api.contacts.service import ContactError, ContactService
from pingpals_api.persistence.repository import InMemoryRepository
from pingpals_api.validation import ValidationError


class Clock:
    def __init__(self) -> None:
        self.t = 1000

    def now(self) -> int:
        self.t += 1
        return self.t


def _setup(quotas: QuotaConfig | None = None):
    repo = InMemoryRepository()
    audit = TamperEvidentAuditLog(time_source=Clock())
    cats = CategoryService(repo, quotas)
    svc = ContactService(repo, audit, quotas)
    default = cats.provision_defaults("alice")
    return repo, audit, cats, svc, default[0]["id"]  # a valid category id


# ---- Contact CRUD (issue 035) ----

def test_create_with_display_name_only_plus_category() -> None:
    repo, _, _, svc, cat = _setup()
    c = svc.create("alice", {"display_name": "Alex", "category_id": cat})
    assert c["display_name"] == "Alex" and c["owner_id"] == "alice"  # AC-01


def test_invalid_email_rejected_no_write() -> None:
    repo, _, _, svc, cat = _setup()
    with pytest.raises(ValidationError):  # AC-03
        svc.create("alice", {"display_name": "A", "category_id": cat, "email": "bad@@x"})
    assert repo.list("alice", "contact") == []


def test_unknown_or_consent_field_rejected() -> None:
    _, _, _, svc, cat = _setup()
    with pytest.raises(ValidationError):  # AC-04 no mass-assignment
        svc.create("alice", {"display_name": "A", "category_id": cat, "consent_email": True})
    with pytest.raises(ValidationError):
        svc.create("alice", {"display_name": "A", "category_id": cat, "owner_id": "attacker"})


def test_cross_user_edit_is_not_found() -> None:
    repo, audit, _, svc, cat = _setup()
    c = svc.create("alice", {"display_name": "Alex", "category_id": cat})
    with pytest.raises(ContactError):  # AC-05
        svc.update("bob", c["id"], {"display_name": "Hacked"})


# ---- Cascade deletion (issue 036) ----

def test_delete_cascades_across_all_tables_with_audit() -> None:
    repo, audit, _, svc, cat = _setup()
    c = svc.create("alice", {"display_name": "Alex", "category_id": cat})
    repo.add("alice", "reminder", "r1", {"contact_id": c["id"]})
    repo.add("alice", "contact_event", "e1", {"contact_id": c["id"]})
    repo.add("alice", "outreach_action", "o1", {"reminder_id": "r1"})

    svc.delete("alice", c["id"])  # AC-01
    assert repo.get("alice", "contact", c["id"]) is None
    assert repo.list("alice", "reminder") == []
    assert repo.list("alice", "contact_event") == []
    assert repo.list("alice", "outreach_action") == []
    assert any(e.action == "deletion" for e in audit.entries)  # AC-03 same-commit audit


def test_delete_cross_user_removes_nothing() -> None:
    repo, _, _, svc, cat = _setup()
    c = svc.create("alice", {"display_name": "Alex", "category_id": cat})
    with pytest.raises(ContactError):  # AC-04
        svc.delete("bob", c["id"])
    assert repo.get("alice", "contact", c["id"]) is not None


def test_delete_fails_closed_when_audit_write_fails() -> None:
    # AC-05: audit write fails (time source down) -> deletion not applied.
    repo = InMemoryRepository()
    dead_audit = TamperEvidentAuditLog(time_source=lambda: (_ for _ in ()).throw(RuntimeError()))
    cats = CategoryService(repo)
    cats.provision_defaults("alice")
    cat = repo.list("alice", "category")[0]["id"]
    svc = ContactService(repo, dead_audit)
    c = svc.create("alice", {"display_name": "Alex", "category_id": cat})
    repo.add("alice", "reminder", "r1", {"contact_id": c["id"]})
    with pytest.raises(TimeUnavailableError):
        svc.delete("alice", c["id"])
    assert repo.get("alice", "contact", c["id"]) is not None   # rolled back
    assert repo.get("alice", "reminder", "r1") is not None


# ---- Categories (issue 037) ----

def test_default_categories_provisioned() -> None:
    repo, _, _, _, _ = _setup()
    names = {c["name"] for c in repo.list("alice", "category")}
    assert {"Best Friend", "Casual Friend", "Family", "Professional"} <= names  # AC-01


def test_category_delete_requires_reassignment_fail_closed() -> None:
    repo, _, cats, svc, cat = _setup()
    svc.create("alice", {"display_name": "Alex", "category_id": cat})
    with pytest.raises(CategoryError):  # AC-03/AC-05 orphan would result
        cats.delete("alice", cat, reassign_to=None)
    assert repo.get("alice", "category", cat) is not None  # nothing modified


def test_category_delete_reassigns_contacts() -> None:
    repo, _, cats, svc, cat = _setup()
    other = cats.create("alice", "Mentors", 45)["id"]
    c = svc.create("alice", {"display_name": "Alex", "category_id": cat})
    cats.delete("alice", cat, reassign_to=other)
    assert repo.get("alice", "category", cat) is None
    assert repo.get("alice", "contact", c["id"])["category_id"] == other  # AC-04 exactly one


def test_category_cross_user_not_found() -> None:
    _, _, cats, _, cat = _setup()
    with pytest.raises(CategoryError):  # AC-06
        cats.rename("bob", cat, "Hacked")


# ---- Quotas (issue 040) ----

def test_contact_quota_rejected_no_partial_write() -> None:
    repo, _, _, svc, cat = _setup(QuotaConfig(max_contacts=1))
    svc.create("alice", {"display_name": "A", "category_id": cat})
    with pytest.raises(QuotaExceeded):  # AC-01/AC-03
        svc.create("alice", {"display_name": "B", "category_id": cat})
    assert len(repo.list("alice", "contact")) == 1


def test_import_batch_limit() -> None:
    q = QuotaConfig(max_import_batch=2)
    with pytest.raises(QuotaExceeded):  # AC-04
        q.check_import_batch(3)
