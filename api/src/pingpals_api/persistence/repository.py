"""Per-user-scoped repository layer (issue 021, SEC-2.2, ARCH Rule 4).

Every operation takes ``owner_id`` as a REQUIRED positional argument — it is structurally
impossible to construct a fetch/mutation for an owned entity without supplying the owner (AC-03),
so Broken Object Level Authorization is prevented at the root rather than per-endpoint. A
cross-user access resolves to not-found (``None`` / ``False``), never another user's data (AC-02).

The concrete PostgreSQL implementation (DECISION 069) lives behind this same interface; the
in-memory implementation is the reference used by tests and keeps the engine fully decoupled
(AC-06). The owner is always taken from the caller (the authenticated session), never from the
record body — defeating owner mass-assignment (AC-05, with issue 020).
"""

from __future__ import annotations

from typing import Any, Protocol

from .entities import OWNER_SCOPED_ENTITIES


class UnknownEntityError(KeyError):
    """Raised when an entity name is not part of the owner-scoped schema."""


class Repository(Protocol):
    """Owner-scoped CRUD. ``owner_id`` is non-optional on every method."""

    def add(self, owner_id: str, entity: str, record_id: str, data: dict) -> dict: ...

    def get(self, owner_id: str, entity: str, record_id: str) -> dict | None: ...

    def list(self, owner_id: str, entity: str) -> list[dict]: ...

    def update(self, owner_id: str, entity: str, record_id: str, changes: dict) -> dict | None: ...

    def delete(self, owner_id: str, entity: str, record_id: str) -> bool: ...


class InMemoryRepository(Repository):
    """Reference implementation enforcing owner scoping. Not for production persistence."""

    def __init__(self) -> None:
        # entity -> owner_id -> record_id -> stored row (owner_id is authoritative on the row)
        self._data: dict[str, dict[str, dict[str, dict]]] = {}

    @staticmethod
    def _check_entity(entity: str) -> None:
        if entity not in OWNER_SCOPED_ENTITIES:
            raise UnknownEntityError(entity)

    def add(self, owner_id: str, entity: str, record_id: str, data: dict) -> dict:
        self._check_entity(entity)
        if not owner_id:
            raise ValueError("owner_id is required")
        # Owner is taken from the caller, never from the body (AC-05): a body owner_id is ignored.
        row = {k: v for k, v in data.items() if k != "owner_id"}
        row["id"] = record_id
        row["owner_id"] = owner_id
        self._data.setdefault(entity, {}).setdefault(owner_id, {})[record_id] = row
        return dict(row)

    def get(self, owner_id: str, entity: str, record_id: str) -> dict | None:
        self._check_entity(entity)
        row = self._data.get(entity, {}).get(owner_id, {}).get(record_id)
        return dict(row) if row is not None else None  # cross-user -> not found

    def list(self, owner_id: str, entity: str) -> list[dict]:
        self._check_entity(entity)
        return [dict(r) for r in self._data.get(entity, {}).get(owner_id, {}).values()]

    def update(self, owner_id: str, entity: str, record_id: str, changes: dict) -> dict | None:
        self._check_entity(entity)
        scope = self._data.get(entity, {}).get(owner_id, {})
        row = scope.get(record_id)
        if row is None:
            return None  # cross-user or missing -> not found
        for k, v in changes.items():
            if k in ("id", "owner_id"):
                continue  # identity/owner are immutable through update
            row[k] = v
        return dict(row)

    def delete(self, owner_id: str, entity: str, record_id: str) -> bool:
        self._check_entity(entity)
        scope = self._data.get(entity, {}).get(owner_id, {})
        return scope.pop(record_id, None) is not None


def assert_no_cross_user(repo: Repository, entity: str, owner_a: str, owner_b: str,
                         record_id: str, data: dict[str, Any]) -> bool:
    """Helper used by isolation tests: B can never see A's row (AC-02)."""
    repo.add(owner_a, entity, record_id, data)
    return repo.get(owner_b, entity, record_id) is None
