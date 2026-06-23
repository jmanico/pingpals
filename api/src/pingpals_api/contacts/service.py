"""Contact CRUD + atomic cascade deletion (issues 035/036, FR-1.1-1.4, PRIV-1.6, SEC-2.2, SEC-8.1).

Create/edit validate against an explicit schema (reject over sanitize, no mass-assignment — a
consent or owner field in the body is rejected); all access is user-scoped (cross-user ⇒
not-found). Deletion is an all-or-nothing cascade across the contact and its reminders, outreach
history, and contact events, with a ``deletion`` audit entry written in the SAME commit: if any
step or the audit write fails, nothing is removed (fail closed).
"""

from __future__ import annotations

import uuid

from ..audit.log import TamperEvidentAuditLog
from ..persistence.repository import Repository
from ..validation import EMAIL_RE, PHONE_RE, Field, ValidationError, validate
from .quotas import QuotaConfig, QuotaExceeded

_DISPLAY_NAME = Field("str", required=True, max_length=120)
_CONTACT_CREATE = {
    "display_name": _DISPLAY_NAME,
    "category_id": Field("str", required=True, max_length=64),
    "email": Field("str", required=False, max_length=254, pattern=EMAIL_RE),
    "phone": Field("str", required=False, max_length=16, pattern=PHONE_RE),
    "notes": Field("str", required=False, max_length=2000),
}
_CONTACT_UPDATE = {name: Field(f.kind, required=False, max_length=f.max_length, pattern=f.pattern)
                   for name, f in _CONTACT_CREATE.items()}

# Dependent entities removed with a contact (PRIV-1.6 / FR-1.3 cascade).
_DEPENDENTS = ("reminder", "contact_event", "outreach_action")


class ContactError(Exception):
    """Contact operation failed (fail closed; no partial write)."""


class ContactService:
    def __init__(
        self,
        repo: Repository,
        audit: TamperEvidentAuditLog,
        quotas: QuotaConfig | None = None,
    ) -> None:
        self._repo = repo
        self._audit = audit
        self._quotas = quotas or QuotaConfig()

    def create(self, owner_id: str, payload: dict) -> dict:
        data = validate(_CONTACT_CREATE, payload)  # rejects unknown/consent fields (AC-04)
        self._quotas.check_contacts(len(self._repo.list(owner_id, "contact")))  # AC quota
        if self._repo.get(owner_id, "category", data["category_id"]) is None:
            raise ContactError("category not found")  # exactly-one-category must be valid (FR-2.4)
        cid = uuid.uuid4().hex
        return self._repo.add(owner_id, "contact", cid, data)

    def update(self, owner_id: str, contact_id: str, payload: dict) -> dict:
        changes = validate(_CONTACT_UPDATE, payload)
        if "category_id" in changes and \
                self._repo.get(owner_id, "category", changes["category_id"]) is None:
            raise ContactError("category not found")
        updated = self._repo.update(owner_id, "contact", contact_id, changes)
        if updated is None:
            raise ContactError("contact not found")  # cross-user/missing (AC-05)
        return updated

    def delete(self, owner_id: str, contact_id: str) -> None:
        if self._repo.get(owner_id, "contact", contact_id) is None:
            raise ContactError("contact not found")  # cross-user/missing -> no write (AC-04)
        self._cascade_delete(owner_id, contact_id)

    def _cascade_delete(self, owner_id: str, contact_id: str) -> None:
        # Build the full deletion plan, then apply atomically with a same-commit audit write.
        reminders = [r for r in self._repo.list(owner_id, "reminder")
                     if r.get("contact_id") == contact_id]
        reminder_ids = {r["id"] for r in reminders}
        plan: list[tuple[str, dict]] = [("contact", {"id": contact_id})]
        plan += [("reminder", r) for r in reminders]
        plan += [("contact_event", e) for e in self._repo.list(owner_id, "contact_event")
                 if e.get("contact_id") == contact_id]
        plan += [("outreach_action", o) for o in self._repo.list(owner_id, "outreach_action")
                 if o.get("reminder_id") in reminder_ids]

        snapshot = [(entity, self._repo.get(owner_id, entity, row["id"]))
                    for entity, row in plan]
        try:
            for entity, row in plan:
                self._repo.delete(owner_id, entity, row["id"])
            # Same-commit audit write (SEC-8.1): if this fails we roll the deletes back (AC-05).
            self._audit.append("deletion", principal=owner_id, object_ref=f"contact:{contact_id}")
        except Exception:
            for entity, row in snapshot:  # all-or-nothing rollback (AC-02)
                if row is not None:
                    self._repo.add(owner_id, entity, row["id"], row)
            raise

    @staticmethod
    def is_validation_error(exc: Exception) -> bool:
        return isinstance(exc, (ValidationError, QuotaExceeded))
