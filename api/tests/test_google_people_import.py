"""Google People import tests (issue 041 / REQ-CONTACTS-030)."""

from __future__ import annotations

import os

import pytest

from pingpals_api.audit.sink import RecordingAuditSink
from pingpals_api.auth.oauth_adapter import OAuthAdapter, OAuthAdapterError, RefreshTokenManager
from pingpals_api.contacts.google_people import (
    CONTACTS_READONLY,
    GooglePeopleImporter,
    StaticPeopleSource,
    parse_person,
)
from pingpals_api.contacts.quotas import QuotaConfig, QuotaExceeded
from pingpals_api.persistence.crypto import (
    AesGcm256,
    CryptoConfig,
    CryptoRegistry,
    CryptoService,
    CryptoUnavailableError,
    KeyStore,
    PurposeBinding,
)
from pingpals_api.persistence.repository import InMemoryRepository
from pingpals_api.persistence.secure_store import Grant, SecureStore
from pingpals_api.validation import ValidationError


class _Keys(KeyStore):
    def __init__(self, k):
        self._k = k

    def data_key(self, ref):
        try:
            return self._k[ref]
        except KeyError as e:
            raise CryptoUnavailableError(ref) from e


def _adapter(scopes):
    reg = CryptoRegistry()
    reg.register(AesGcm256())
    crypto = CryptoService(reg, CryptoConfig({"token:google": PurposeBinding("AES-256-GCM", "k")}),
                           _Keys({"k": os.urandom(32)}))
    store = SecureStore(crypto, [Grant("google-people", frozenset({"token:google"}))],
                        RecordingAuditSink())
    return OAuthAdapter("google-people", "google", scopes, store, RefreshTokenManager())


def _person(rid, name, email=None, phone=None, extra=None):
    p = {"resourceName": rid, "names": [{"displayName": name}]}
    if email:
        p["emailAddresses"] = [{"value": email}]
    if phone:
        p["phoneNumbers"] = [{"value": phone}]
    if extra:
        p.update(extra)
    return p


def _importer(scopes=frozenset({CONTACTS_READONLY}), quotas=None):
    repo = InMemoryRepository()
    repo.add("alice", "category", "cat1", {"name": "Imported", "default_cadence_days": 60})
    return repo, GooglePeopleImporter(_adapter(scopes), repo, "cat1", quotas)


def test_scope_pinned_to_contacts_readonly() -> None:
    _, imp = _importer()
    assert imp.authorization_scopes() == frozenset({CONTACTS_READONLY})  # AC-01


def test_scope_outside_set_fails_closed() -> None:
    _, imp = _importer(scopes=frozenset({"https://www.googleapis.com/auth/gmail.modify"}))
    with pytest.raises(OAuthAdapterError):  # AC-01
        imp.authorization_scopes()


def test_only_minimal_fields_stored() -> None:
    repo, imp = _importer()
    person = _person("people/1", "Alex", "alex@example.com", "+15551234567",
                     extra={"biographies": [{"value": "secret"}], "addresses": [{"city": "X"}]})
    imp.import_from("alice", StaticPeopleSource([[person]]))
    row = repo.list("alice", "contact")[0]
    assert row["display_name"] == "Alex" and row["email"] == "alex@example.com"
    assert "biographies" not in row and "addresses" not in row  # AC-02 no unrelated data


def test_dedupe_by_provider_id() -> None:
    repo, imp = _importer()
    p = _person("people/1", "Alex", "alex@example.com")
    res = imp.import_from("alice", StaticPeopleSource([[p], [p]]))  # same id twice
    assert res == {"imported": 1, "skipped": 1}  # AC-03
    assert len(repo.list("alice", "contact")) == 1


def test_malformed_record_rejected() -> None:
    _, imp = _importer()
    bad = {"resourceName": "people/2"}  # no name
    with pytest.raises(ValidationError):  # AC-05
        imp.import_from("alice", StaticPeopleSource([[bad]]))


def test_over_batch_bound_rejected() -> None:
    _, imp = _importer(quotas=QuotaConfig(max_import_batch=1))
    page = [_person("people/1", "A"), _person("people/2", "B")]
    with pytest.raises(QuotaExceeded):  # AC-04
        imp.import_from("alice", StaticPeopleSource([page]))


def test_parse_person_drops_unrelated_fields() -> None:
    parsed = parse_person(_person("people/9", "Sam", "sam@example.com", "+15550000000",
                                  extra={"photos": [{"url": "x"}]}))
    assert set(parsed) == {"provider_id", "display_name", "email", "phone"}
