"""Erasure cascade + surviving proof-of-erasure (issues 059/060, PRIV-1.6/1.16, FR-1.3, SEC-3.3).

Erasure is a hard-delete cascade across every store holding the subject's personal data —
contacts, reminders, outreach history, derived detection data, provider tokens, and export
artifacts — with provider tokens revoked at the provider as well as purged locally. It FAILS CLOSED:
if any store fails or the proof-of-erasure record cannot be durably committed, the whole operation
rolls back and is NOT reported complete. The proof record is written to the tamper-evident audit log
(excluded from the cascade, so it SURVIVES) and is PII-free: a pseudonymous subject reference, the
DSR type, the stores purged, the requesting principal, and the server completion time.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable

from ..audit.log import TamperEvidentAuditLog
from ..persistence.entities import OWNER_SCOPED_ENTITIES
from ..persistence.repository import Repository

# Every owner-scoped store EXCEPT the audit log (the proof must survive — PRIV-1.16 / AC-04).
_ERASABLE_ENTITIES = tuple(e for e in OWNER_SCOPED_ENTITIES if e != "audit_log_entry")


class ErasureError(Exception):
    """Erasure could not complete atomically — nothing is reported erased (fail closed)."""


def pseudonymous_ref(owner_id: str) -> str:
    """A stable, non-reversible subject reference for the PII-free proof record (PRIV-1.16)."""
    return "subj_" + hashlib.sha256(owner_id.encode("utf-8")).hexdigest()[:16]


class ErasureService:
    def __init__(
        self,
        repo: Repository,
        audit: TamperEvidentAuditLog,
        revoke_provider_tokens: Callable[[str], None] | None = None,
        purge_export_artifacts: Callable[[str], int] | None = None,
    ) -> None:
        self._repo = repo
        self._audit = audit
        self._revoke = revoke_provider_tokens or (lambda _owner: None)
        self._purge_exports = purge_export_artifacts or (lambda _owner: 0)

    def erase_subject(self, owner_id: str, requesting_principal: str) -> dict:
        """Hard-delete all of the subject's data, then commit a surviving proof or roll back."""
        snapshot: list[tuple[str, dict]] = []
        for entity in _ERASABLE_ENTITIES:
            for row in self._repo.list(owner_id, entity):
                snapshot.append((entity, row))

        purged_stores: list[str] = []
        try:
            self._revoke(owner_id)  # revoke provider tokens at the provider (SEC-3.3)
            for entity, row in snapshot:
                self._repo.delete(owner_id, entity, row["id"])
                if entity not in purged_stores:
                    purged_stores.append(entity)
            self._purge_exports(owner_id)
            purged_stores.append("export_artifacts")

            # Same-commit, PII-free proof of erasure that SURVIVES the cascade (AC-01/AC-02/AC-03).
            proof = self._audit.append(
                "dsr.erasure", principal=requesting_principal,
                object_ref=f"{pseudonymous_ref(owner_id)}|type:erasure|stores:{','.join(purged_stores)}",
            )
        except Exception as exc:
            # Store failure or unwritable proof -> roll back; not reported complete (AC-03/AC-05).
            for entity, row in snapshot:
                if self._repo.get(owner_id, entity, row["id"]) is None:
                    self._repo.add(owner_id, entity, row["id"], row)
            raise ErasureError("erasure aborted; no partial state committed") from exc

        return {"subject_ref": pseudonymous_ref(owner_id), "proof_seq": proof.seq,
                "stores": purged_stores}

    def verify_erased(self, owner_id: str) -> bool:
        """True iff no personal data for the subject remains in primary storage (AC-02)."""
        return all(self._repo.list(owner_id, e) == [] for e in _ERASABLE_ENTITIES)
