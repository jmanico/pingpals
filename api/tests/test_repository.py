"""Per-user repository isolation + schema tests (issue 021 / REQ-FND-010)."""

from __future__ import annotations

import pytest

from pingpals_api.persistence.entities import (
    OWNER_SCOPED_ENTITIES,
    SCHEMA,
    Classification,
)
from pingpals_api.persistence.repository import (
    InMemoryRepository,
    UnknownEntityError,
    assert_no_cross_user,
)

EXPECTED_ENTITIES = {
    "user", "contact", "category", "cadence", "reminder", "consent_record",
    "contact_event", "outreach_action", "provider_token", "audit_log_entry",
}


def test_owner_scoped_crud_roundtrip() -> None:
    repo = InMemoryRepository()
    repo.add("user-A", "contact", "c1", {"display_name": "Alex"})
    assert repo.get("user-A", "contact", "c1")["display_name"] == "Alex"  # AC-01
    assert len(repo.list("user-A", "contact")) == 1
    repo.update("user-A", "contact", "c1", {"display_name": "Alexandra"})
    assert repo.get("user-A", "contact", "c1")["display_name"] == "Alexandra"
    assert repo.delete("user-A", "contact", "c1") is True
    assert repo.get("user-A", "contact", "c1") is None


def test_cross_user_access_is_not_found_for_every_owned_entity() -> None:
    # AC-02 / SEC-2.2: B can never read A's row, for every owner-scoped entity.
    for entity in OWNER_SCOPED_ENTITIES:
        repo = InMemoryRepository()
        assert assert_no_cross_user(repo, entity, "user-A", "user-B", "x1", {"v": 1}) is True
        assert repo.update("user-B", entity, "x1", {"v": 2}) is None
        assert repo.delete("user-B", entity, "x1") is False


def test_owner_id_is_structurally_required() -> None:
    # AC-03: cannot construct an access without the owning user (non-optional positional).
    repo = InMemoryRepository()
    with pytest.raises(TypeError):
        repo.get(entity="contact", record_id="c1")  # type: ignore[call-arg]


def test_owner_taken_from_caller_not_body() -> None:
    # AC-05: a body-supplied owner_id is ignored; the caller's owner is authoritative.
    repo = InMemoryRepository()
    row = repo.add("user-A", "contact", "c1", {"display_name": "Alex", "owner_id": "attacker"})
    assert row["owner_id"] == "user-A"
    # owner is immutable through update, too.
    repo.update("user-A", "contact", "c1", {"owner_id": "attacker"})
    assert repo.get("user-A", "contact", "c1")["owner_id"] == "user-A"


def test_schema_has_all_ten_entities_with_owner_fks_and_classifications() -> None:
    # AC-04: ten entities; every owned entity carries owner_id; classifications are set.
    assert set(SCHEMA) == EXPECTED_ENTITIES
    for name, spec in SCHEMA.items():
        if spec.owner_scoped:
            assert "owner_id" in spec.field_names(), f"{name} missing owner_id FK"
    # Restricted fields are classified as such (provider token ciphertext, contact PII).
    assert any(
        f.classification is Classification.RESTRICTED and f.name == "ciphertext"
        for f in SCHEMA["provider_token"].fields
    )
    assert any(
        f.classification is Classification.RESTRICTED and f.name == "display_name"
        for f in SCHEMA["contact"].fields
    )


def test_unknown_entity_rejected() -> None:
    repo = InMemoryRepository()
    with pytest.raises(UnknownEntityError):
        repo.add("user-A", "not_an_entity", "x", {})
