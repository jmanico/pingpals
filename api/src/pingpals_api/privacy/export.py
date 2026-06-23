"""Machine-readable data export (issue 057, PRIV-1.5, SEC-2.2).

Produces a complete, machine-readable (JSON) artifact of ALL personal data held for the requesting
user — contacts, categories, cadence, consent, and history — and NO other user's data. Generation
writes a DSR audit event and is rate-limited at the HTTP boundary (issue 024). The artifact
round-trips the user's records.
"""

from __future__ import annotations

import json

from ..audit.log import TamperEvidentAuditLog
from ..persistence.entities import OWNER_SCOPED_ENTITIES
from ..persistence.repository import Repository

EXPORT_SCHEMA_VERSION = "1.0"
# Entities included in a portability export (audit log is excluded — it is accountability data).
_EXPORTED_ENTITIES = tuple(e for e in OWNER_SCOPED_ENTITIES if e != "audit_log_entry")


class ExportService:
    def __init__(self, repo: Repository, audit: TamperEvidentAuditLog) -> None:
        self._repo = repo
        self._audit = audit

    def build_export(self, owner_id: str) -> dict:
        """Return a complete, user-scoped export object (AC-01/AC-02/AC-05)."""
        data = {entity: self._repo.list(owner_id, entity) for entity in _EXPORTED_ENTITIES}
        self._audit.append("dsr.export", principal=owner_id, object_ref="export")  # AC-03
        return {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "subject": owner_id,
            "data": data,
        }

    def to_json(self, owner_id: str) -> bytes:
        return json.dumps(self.build_export(owner_id), sort_keys=True).encode("utf-8")
