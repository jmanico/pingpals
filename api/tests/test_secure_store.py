"""Partitioned, audited at-rest envelope tests (issue 022 / REQ-FND-011)."""

from __future__ import annotations

import os

import pytest

from pingpals_api.audit.sink import RecordingAuditSink
from pingpals_api.persistence.crypto import (
    DENY_ALL,
    AesGcm256,
    CryptoConfig,
    CryptoRegistry,
    CryptoService,
    CryptoUnavailableError,
    KeyStore,
    PurposeBinding,
)
from pingpals_api.persistence.secure_store import DecryptDenied, Grant, SecureStore

GOOGLE = "token:google"
MICROSOFT = "token:microsoft"
PURPOSES = (GOOGLE, MICROSOFT)


class InMemoryKeyStore(KeyStore):
    """DEV/TEST ONLY — production resolves keys through a managed KMS (DECISION 072)."""

    def __init__(self, keys: dict[str, bytes]) -> None:
        self._keys = dict(keys)

    def data_key(self, key_reference: str) -> bytes:
        try:
            return self._keys[key_reference]
        except KeyError as exc:
            raise CryptoUnavailableError(key_reference) from exc


def _crypto(key_store: KeyStore) -> CryptoService:
    reg = CryptoRegistry()
    reg.register(AesGcm256())
    config = CryptoConfig({
        GOOGLE: PurposeBinding("AES-256-GCM", "kref-google"),
        MICROSOFT: PurposeBinding("AES-256-GCM", "kref-microsoft"),
    })
    return CryptoService(reg, config, key_store)


def _store_with_managed_keys() -> tuple[SecureStore, RecordingAuditSink]:
    keys = {"kref-google": os.urandom(32), "kref-microsoft": os.urandom(32)}
    audit = RecordingAuditSink()
    store = SecureStore(
        _crypto(InMemoryKeyStore(keys)),
        grants=[
            Grant("google-adapter", frozenset({GOOGLE})),
            Grant("microsoft-adapter", frozenset({MICROSOFT})),
        ],
        audit=audit,
    )
    return store, audit


def test_granted_component_roundtrips_and_is_audited() -> None:
    store, audit = _store_with_managed_keys()
    ct = store.encrypt("google-adapter", GOOGLE, b"refresh-token-123", object_ref="tok-1")
    assert ct != b"refresh-token-123"  # AC-01: stored as ciphertext
    assert store.decrypt("google-adapter", GOOGLE, ct, object_ref="tok-1") == b"refresh-token-123"
    # AC-04: success audited with component + purpose, NO plaintext anywhere in the event.
    allowed = [e for e in audit.events if e.outcome == "allowed"]
    assert any(e.action == "crypto.decrypt" and e.principal == "google-adapter" for e in allowed)
    for e in audit.events:
        serialized = e.action + e.principal + e.purpose + (e.object_ref or "")
        assert "refresh-token-123" not in serialized


def test_cross_adapter_decrypt_denied_and_audited() -> None:
    # AC-03: the google adapter may not decrypt microsoft's purpose.
    store, audit = _store_with_managed_keys()
    ct = store.encrypt("microsoft-adapter", MICROSOFT, b"ms-token")
    with pytest.raises(DecryptDenied):
        store.decrypt("google-adapter", MICROSOFT, ct)
    assert any(e.action == "crypto.decrypt.denied" and e.outcome == "denied" for e in audit.events)


def test_ungranted_component_denied_by_default() -> None:
    # AC-05: no grant -> denied (no implicit/app-wide decrypt role).
    store, _ = _store_with_managed_keys()
    with pytest.raises(DecryptDenied):
        store.decrypt("unknown-component", GOOGLE, b"\x00" * 40)


def test_no_app_wide_decrypt_role() -> None:
    store, _ = _store_with_managed_keys()
    assert store.grants_all_purposes(PURPOSES) is False  # no single role decrypts every class
    # sanity: the detector would catch an app-wide role if one were (wrongly) created.
    bad = SecureStore(
        _crypto(InMemoryKeyStore({})),
        grants=[Grant("god-role", frozenset(PURPOSES))],
        audit=RecordingAuditSink(),
    )
    assert bad.grants_all_purposes(PURPOSES) is True


def test_backup_unreadable_without_managed_keys() -> None:
    # AC-02 / SEC-5.6: ciphertext is opaque without the managed key store.
    store, _ = _store_with_managed_keys()
    ct = store.encrypt("google-adapter", GOOGLE, b"secret")
    # A store wired to the deny-all key store (no managed keys) cannot read the backup.
    no_keys = SecureStore(
        _crypto(DENY_ALL),
        grants=[Grant("google-adapter", frozenset({GOOGLE}))],
        audit=RecordingAuditSink(),
    )
    with pytest.raises(CryptoUnavailableError):
        no_keys.decrypt("google-adapter", GOOGLE, ct)
