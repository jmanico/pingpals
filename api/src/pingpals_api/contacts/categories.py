"""Category management (issue 037, FR-2.1/2.2/2.3/2.4).

Ships the four default categories with configurable default cadences on provisioning; supports
custom category CRUD scoped to the user. Deleting a category REQUIRES reassignment of its contacts
to another category and FAILS CLOSED if any contact would be left without a category. A contact
belongs to exactly one category at a time (single ``category_id``).
"""

from __future__ import annotations

import uuid

from ..persistence.repository import Repository
from .quotas import QuotaConfig

DEFAULT_CATEGORIES: tuple[tuple[str, int], ...] = (
    ("Best Friend", 14),
    ("Casual Friend", 60),
    ("Family", 30),
    ("Professional", 90),
)


class CategoryError(Exception):
    """Category operation failed (fail closed; no partial write)."""


class CategoryService:
    def __init__(self, repo: Repository, quotas: QuotaConfig | None = None) -> None:
        self._repo = repo
        self._quotas = quotas or QuotaConfig()

    def provision_defaults(self, owner_id: str) -> list[dict]:
        created = []
        for name, cadence_days in DEFAULT_CATEGORIES:
            created.append(self._create(owner_id, name, cadence_days))
        return created

    def create(self, owner_id: str, name: str, default_cadence_days: int) -> dict:
        existing = self._repo.list(owner_id, "category")
        self._quotas.check_categories(len(existing))
        if any(c["name"] == name for c in existing):
            raise CategoryError("a category with that name already exists")
        return self._create(owner_id, name, default_cadence_days)

    def _create(self, owner_id: str, name: str, cadence_days: int) -> dict:
        cid = uuid.uuid4().hex
        return self._repo.add(owner_id, "category", cid,
                              {"name": name, "default_cadence_days": cadence_days})

    def rename(self, owner_id: str, category_id: str, new_name: str) -> dict:
        updated = self._repo.update(owner_id, "category", category_id, {"name": new_name})
        if updated is None:
            raise CategoryError("category not found")  # cross-user or missing (AC-06)
        return updated

    def delete(self, owner_id: str, category_id: str, reassign_to: str | None) -> None:
        target = self._repo.get(owner_id, "category", category_id)
        if target is None:
            raise CategoryError("category not found")  # AC-06
        contacts = [c for c in self._repo.list(owner_id, "contact")
                    if c.get("category_id") == category_id]
        if contacts:
            if reassign_to is None or self._repo.get(owner_id, "category", reassign_to) is None:
                # fail closed: no orphaned contacts, modify nothing (AC-03/AC-05)
                raise CategoryError("a valid reassignment category is required")
            for c in contacts:
                self._repo.update(owner_id, "contact", c["id"], {"category_id": reassign_to})
        self._repo.delete(owner_id, "category", category_id)
