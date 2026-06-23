"""Automated retention job (issue 062, PRIV-1.9, SEC-8.4).

Deletes operational-PII records whose retention has elapsed and logs the action. Security/DSR/
accountability events are governed by a DISTINCT accountability retention period that is not shorter
than operational-PII retention, so they survive past operational expiry. Aging out audit data
preserves tamper-evidence: only sealed, independently verifiable segments are removed, the surviving
chain is re-anchored, and the purge itself is logged. If the chain cannot be kept verifiable the
job HALTS and alerts (no truncate/splice — fail closed).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..audit.log import TamperEvidentAuditLog
from ..persistence.repository import Repository

# Operational-PII entities aged by record/event time.
_OPERATIONAL_ENTITIES = ("reminder", "contact_event", "outreach_action")


class RetentionError(Exception):
    """The retention job could not complete safely — halted (fail closed)."""


@dataclass(frozen=True)
class RetentionConfig:
    operational_retention_seconds: int
    accountability_retention_seconds: int

    def __post_init__(self) -> None:
        if self.accountability_retention_seconds < self.operational_retention_seconds:
            raise RetentionError("accountability retention must not be shorter than operational")


class RetentionJob:
    def __init__(
        self,
        repo: Repository,
        audit: TamperEvidentAuditLog,
        config: RetentionConfig,
        on_alert: Callable[[str], None] | None = None,
    ) -> None:
        self._repo = repo
        self._audit = audit
        self._config = config
        self._alert = on_alert or (lambda _m: None)

    def run(self, owner_ids: list[str], now: int) -> dict:
        op_cutoff = now - self._config.operational_retention_seconds
        deleted = 0
        for owner_id in owner_ids:
            for entity in _OPERATIONAL_ENTITIES:
                for row in self._repo.list(owner_id, entity):
                    t = row.get("record_time") or row.get("due_at") or 0
                    if t and t < op_cutoff:
                        self._repo.delete(owner_id, entity, row["id"])
                        deleted += 1
        if deleted:
            self._audit.append("retention.purge", principal="system",
                               object_ref=f"operational:{deleted}")  # AC-01 log the action

        # Age out audit data as sealed segments, keeping accountability events (AC-02/AC-03/AC-05).
        acc_cutoff_seq = self._accountability_cutoff_seq(now)
        if acc_cutoff_seq > 0:
            self._audit.seal_and_purge(keep_from_seq=acc_cutoff_seq)
            if not self._audit.verify():  # chain must still verify end to end (AC-04)
                self._alert("audit chain failed to verify after retention purge")
                raise RetentionError("retention purge would break the audit chain")
        return {"operational_deleted": deleted}

    def _accountability_cutoff_seq(self, now: int) -> int:
        # Entries older than the accountability window AND not accountability actions are eligible;
        # seal_and_purge itself preserves accountability actions, so we pass a seq boundary.
        acc_cutoff = now - self._config.accountability_retention_seconds
        eligible = [e.seq for e in self._audit.entries if e.record_time < acc_cutoff]
        return (max(eligible) + 1) if eligible else 0
