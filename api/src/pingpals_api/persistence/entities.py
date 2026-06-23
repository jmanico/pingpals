"""Core entity schema with §3 data classification (issue 021).

A declarative description of the ten core entities (REQUIREMENTS.md ARCHITECTURE data model) and
the data classification (§3) of each field. The concrete PostgreSQL DDL / migration is generated
from this registry (DECISION 069 resolved = PostgreSQL, behind the repository interface — issue
021 AC-06); keeping the schema declarative lets the owner-scoping and classification invariants be
asserted without a live database.

Every owned entity carries ``owner_id`` (FK to ``user``) — the structural basis for SEC-2.2 /
ARCH Rule 4. ``User`` is the owner root and is not itself owner-scoped.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Classification(str, Enum):
    """REQUIREMENTS.md §3 data classification."""

    RESTRICTED = "restricted"      # contact PII, OAuth tokens, consent records, audit logs
    CONFIDENTIAL = "confidential"  # account credentials / session material
    INTERNAL = "internal"          # non-personal identifiers, aggregate metrics


@dataclass(frozen=True)
class FieldSpec:
    name: str
    classification: Classification
    nullable: bool = False


@dataclass(frozen=True)
class EntitySpec:
    name: str
    owner_scoped: bool
    fields: tuple[FieldSpec, ...]

    def field_names(self) -> tuple[str, ...]:
        return tuple(f.name for f in self.fields)


def _r(name: str, nullable: bool = False) -> FieldSpec:
    return FieldSpec(name, Classification.RESTRICTED, nullable)


def _c(name: str, nullable: bool = False) -> FieldSpec:
    return FieldSpec(name, Classification.CONFIDENTIAL, nullable)


def _i(name: str, nullable: bool = False) -> FieldSpec:
    return FieldSpec(name, Classification.INTERNAL, nullable)


# The ten core entities (ARCHITECTURE.md data model). Owner FK is implicit for owner_scoped=True.
SCHEMA: dict[str, EntitySpec] = {
    "user": EntitySpec("user", owner_scoped=False, fields=(
        _i("id"),
        _c("oidc_sub"),               # immutable IdP subject (account key, SEC INT-1.9)
        _c("oidc_iss"),
        _r("email", nullable=True),   # non-authoritative display attribute only
        _i("created_at"),
    )),
    "contact": EntitySpec("contact", owner_scoped=True, fields=(
        _i("id"), _i("owner_id"),
        _r("display_name"), _r("email", nullable=True), _r("phone", nullable=True),
        _i("category_id"), _r("notes", nullable=True),
        _i("provider", nullable=True), _i("provider_id", nullable=True),  # import dedup (INT-4.2)
        _i("last_contacted_at", nullable=True),  # cadence clock (FR-4.2)
        _i("cadence_override_days", nullable=True),  # per-contact override (FR-3.2)
    )),
    "category": EntitySpec("category", owner_scoped=True, fields=(
        _i("id"), _i("owner_id"), _r("name"), _i("default_cadence_id", nullable=True),
    )),
    "cadence": EntitySpec("cadence", owner_scoped=True, fields=(
        _i("id"), _i("owner_id"),
        _i("interval_days"), _i("preferred_dow", nullable=True),
        _i("send_window_start", nullable=True), _i("send_window_end", nullable=True),
    )),
    "reminder": EntitySpec("reminder", owner_scoped=True, fields=(
        _i("id"), _i("owner_id"), _i("contact_id"),
        _i("due_at"), _i("channel"), _i("status"), _i("idempotency_key"),
    )),
    "consent_record": EntitySpec("consent_record", owner_scoped=True, fields=(
        _i("id"), _i("owner_id"),
        _r("channel"), _r("action"), _i("notice_version"), _i("record_time"),
    )),
    "contact_event": EntitySpec("contact_event", owner_scoped=True, fields=(
        _i("id"), _i("owner_id"), _i("contact_id"),
        _i("asserted_time", nullable=True), _i("record_time"),
    )),
    "outreach_action": EntitySpec("outreach_action", owner_scoped=True, fields=(
        _i("id"), _i("owner_id"), _i("reminder_id"), _i("kind"), _r("target"),
    )),
    "provider_token": EntitySpec("provider_token", owner_scoped=True, fields=(
        _i("id"), _i("owner_id"), _i("provider"),
        _r("ciphertext"),            # AES-256-GCM ciphertext (issue 022); never plaintext
        _i("key_reference"),         # managed-key-store handle, not key material
    )),
    "audit_log_entry": EntitySpec("audit_log_entry", owner_scoped=True, fields=(
        _i("id"), FieldSpec("owner_id", Classification.INTERNAL, nullable=True),  # null = system
        _r("action"), _r("object_ref"), _r("principal"),
        _i("record_time"), _i("prev_hash"), _i("hash"),
    )),
}

#: Entities that MUST be accessed only with an owning user (BOLA defense, SEC-2.2).
OWNER_SCOPED_ENTITIES: tuple[str, ...] = tuple(
    name for name, spec in SCHEMA.items() if spec.owner_scoped
)


@dataclass
class Record:
    """A persisted row. ``owner_id`` is set by the repository from the caller, never the body."""

    id: str
    owner_id: str | None
    data: dict = field(default_factory=dict)
