"""Google People contact import (issue 041, FR-1.5, INT-4.1/4.2, SEC-4.1, SEC-6.3).

Imports at the contacts-read scope ONLY (verified against the adapter's pinned least-privilege
declaration). Only display name, phone, email, and the stable provider id are stored — no unrelated
profile data. Contacts are deduplicated by provider id. The address book is streamed/paginated
against the per-batch quota rather than loaded wholesale; an over-bound batch or a malformed record
is rejected (reject over sanitize) with no partial write. Rate/concurrency limits (issue 024) gate
the HTTP endpoint. The concrete People API HTTP client is injected via ``PeopleSource``.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Iterator
from typing import Protocol

from ..auth.oauth_adapter import OAuthAdapter
from ..persistence.repository import Repository
from ..validation import EMAIL_RE, PHONE_RE, Field, ValidationError, validate
from .quotas import QuotaConfig

CONTACTS_READONLY = "https://www.googleapis.com/auth/contacts.readonly"

_IMPORT_SCHEMA = {
    "provider_id": Field("str", required=True, max_length=128),
    "display_name": Field("str", required=True, max_length=120),
    "email": Field("str", required=False, max_length=254, pattern=EMAIL_RE),
    "phone": Field("str", required=False, max_length=16, pattern=PHONE_RE),
}


class ImportError_(Exception):
    """Import failed (fail closed; no partial write)."""


class PeopleSource(Protocol):
    """Yields pages (lists) of raw Google People ``person`` dicts. Concrete HTTP client deferred."""

    def pages(self) -> Iterator[list[dict]]: ...


def parse_person(person: dict) -> dict:
    """Extract ONLY name/phone/email/provider id (INT-4.2); reject malformed (AC-05)."""
    provider_id = person.get("resourceName")
    names = person.get("names") or []
    display = names[0].get("displayName") if names else None
    emails = person.get("emailAddresses") or []
    phones = person.get("phoneNumbers") or []
    candidate = {
        "provider_id": provider_id,
        "display_name": display,
        # Only first email/phone; drop unrelated profile data entirely.
        **({"email": emails[0]["value"]} if emails and emails[0].get("value") else {}),
        **({"phone": phones[0]["value"]} if phones and phones[0].get("value") else {}),
    }
    # Validation rejects malformed/over-bound fields; never coerces (AC-05).
    return validate(_IMPORT_SCHEMA, {k: v for k, v in candidate.items() if v is not None})


class GooglePeopleImporter:
    def __init__(
        self,
        adapter: OAuthAdapter,
        repo: Repository,
        category_id: str,
        quotas: QuotaConfig | None = None,
    ) -> None:
        self._adapter = adapter
        self._repo = repo
        self._category_id = category_id
        self._quotas = quotas or QuotaConfig()

    def authorization_scopes(self) -> frozenset[str]:
        """Scope-pin to contacts-read only; any out-of-set scope fails closed (AC-01)."""
        return self._adapter.build_scopes(frozenset({CONTACTS_READONLY}))

    def import_from(self, owner_id: str, source: PeopleSource) -> dict:
        existing = self._repo.list(owner_id, "contact")
        seen_provider_ids = {c.get("provider_id") for c in existing if c.get("provider_id")}
        contact_count = len(existing)
        imported = 0
        skipped = 0

        for page in source.pages():
            self._quotas.check_import_batch(len(page))  # per-batch bound (AC-04); no wholesale load
            for person in page:
                parsed = parse_person(person)  # raises ValidationError on malformed (AC-05)
                if parsed["provider_id"] in seen_provider_ids:
                    skipped += 1  # dedupe by provider id (AC-03)
                    continue
                self._quotas.check_contacts(contact_count)  # total quota (no partial write)
                self._repo.add(owner_id, "contact", uuid.uuid4().hex, {
                    "display_name": parsed["display_name"],
                    "email": parsed.get("email"),
                    "phone": parsed.get("phone"),
                    "category_id": self._category_id,
                    "provider": self._adapter.provider,
                    "provider_id": parsed["provider_id"],
                })
                seen_provider_ids.add(parsed["provider_id"])
                contact_count += 1
                imported += 1
        return {"imported": imported, "skipped": skipped}


class StaticPeopleSource(PeopleSource):
    """Test/bootstrap source backed by in-memory pages."""

    def __init__(self, pages: Iterable[list[dict]]) -> None:
        self._pages = [list(p) for p in pages]

    def pages(self) -> Iterator[list[dict]]:
        yield from self._pages


__all__ = [
    "CONTACTS_READONLY",
    "GooglePeopleImporter",
    "ImportError_",
    "PeopleSource",
    "StaticPeopleSource",
    "ValidationError",
    "parse_person",
]
