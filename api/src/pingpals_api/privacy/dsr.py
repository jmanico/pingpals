"""Data-subject-rights endpoints (issue 061, PRIV-1.3/1.4, GDPR Arts. 15-21).

Implements the user's DSR: access & portability (delegates to export, issue 057), rectification
(Art. 16, audited), restriction (Art. 18) and objection (Art. 21) flags that suppress
processing/delivery (fail closed), and erasure (delegates to the cascade + proof, issues 059/060).
All actions are scoped to the requesting user; a DSR targeting another user's data returns
not-found. Contact (non-user) DSRs use the MVP controller-mediated model: the controlling user
erases the contact; direct identity-verified intake remains DECISION 075.
"""

from __future__ import annotations

from ..audit.log import TamperEvidentAuditLog
from ..persistence.repository import Repository
from ..validation import Field, validate
from .erasure import ErasureService
from .export import ExportService

_RECTIFY_SCHEMA = {
    "display_name": Field("str", required=False, max_length=120),
    "email": Field("str", required=False, max_length=254),
    "phone": Field("str", required=False, max_length=16),
    "notes": Field("str", required=False, max_length=2000),
}


class DSRError(Exception):
    """A DSR action failed (fail closed; no state change)."""


class DSRService:
    def __init__(
        self,
        repo: Repository,
        audit: TamperEvidentAuditLog,
        export: ExportService,
        erasure: ErasureService,
    ) -> None:
        self._repo = repo
        self._audit = audit
        self._export = export
        self._erasure = erasure
        # (owner_id, flag) where flag is "restrict" or "object"
        self._restricted: set[tuple[str, str]] = set()

    # Art. 15 / 20
    def access(self, owner_id: str) -> dict:
        return self._export.build_export(owner_id)

    # Art. 16
    def rectify_contact(self, owner_id: str, contact_id: str, changes: dict) -> dict:
        data = validate(_RECTIFY_SCHEMA, changes)  # no mass-assignment
        updated = self._repo.update(owner_id, "contact", contact_id, data)
        if updated is None:
            raise DSRError("contact not found")  # cross-user/missing (AC-05)
        self._audit.append("contact.rectify", principal=owner_id,
                           object_ref=f"contact:{contact_id}")  # AC-02
        return updated

    # Art. 18 / 21
    def set_restriction(self, owner_id: str, restricted: bool) -> None:
        self._set_flag(owner_id, "restrict", restricted)

    def set_objection(self, owner_id: str, objected: bool) -> None:
        self._set_flag(owner_id, "object", objected)

    def _set_flag(self, owner_id: str, flag: str, on: bool) -> None:
        key = (owner_id, flag)
        if on:
            self._restricted.add(key)
        else:
            self._restricted.discard(key)
        self._audit.append(f"dsr.{flag}", principal=owner_id, object_ref=f"on:{on}")

    def processing_allowed(self, owner_id: str) -> bool:
        """False if restriction/objection is set — scheduler/delivery then suppress (AC-03)."""
        return (owner_id, "restrict") not in self._restricted \
            and (owner_id, "object") not in self._restricted

    # Art. 17
    def erase_contact(self, owner_id: str, contact_id: str) -> dict:
        """Controller-mediated contact erasure (MVP default; AC-04)."""
        if self._repo.get(owner_id, "contact", contact_id) is None:
            raise DSRError("contact not found")  # AC-05
        # Cascade just this contact's dependents + the contact row.
        for entity in ("reminder", "contact_event", "outreach_action"):
            for row in self._repo.list(owner_id, entity):
                if row.get("contact_id") == contact_id or row.get("reminder_id"):
                    self._repo.delete(owner_id, entity, row["id"])
        self._repo.delete(owner_id, "contact", contact_id)
        self._audit.append("dsr.erasure", principal=owner_id, object_ref=f"contact:{contact_id}")
        return {"erased": contact_id}

    def erase_account(self, owner_id: str, requesting_principal: str) -> dict:
        return self._erasure.erase_subject(owner_id, requesting_principal)
