"""OAuth provider adapter tests (issue 033 / REQ-AUTH-022)."""

from __future__ import annotations

import os

import pytest

from pingpals_api.audit.sink import RecordingAuditSink
from pingpals_api.auth.oauth_adapter import (
    OAuthAdapter,
    OAuthAdapterError,
    RefreshReplayError,
    RefreshTokenManager,
)
from pingpals_api.persistence.crypto import (
    AesGcm256,
    CryptoConfig,
    CryptoRegistry,
    CryptoService,
    CryptoUnavailableError,
    KeyStore,
    PurposeBinding,
)
from pingpals_api.persistence.secure_store import Grant, SecureStore

PINNED = frozenset({"https://www.googleapis.com/auth/contacts.readonly"})


class _Keys(KeyStore):
    def __init__(self, keys):
        self._keys = keys

    def data_key(self, key_reference: str) -> bytes:
        try:
            return self._keys[key_reference]
        except KeyError as e:
            raise CryptoUnavailableError(key_reference) from e


def _adapter() -> OAuthAdapter:
    reg = CryptoRegistry()
    reg.register(AesGcm256())
    crypto = CryptoService(
        reg, CryptoConfig({"token:google": PurposeBinding("AES-256-GCM", "kref")}),
        _Keys({"kref": os.urandom(32)}),
    )
    store = SecureStore(crypto, [Grant("google-people", frozenset({"token:google"}))],
                        RecordingAuditSink())
    return OAuthAdapter("google-people", "google", PINNED, store, RefreshTokenManager())


def test_scopes_pinned_to_declared_set() -> None:
    a = _adapter()
    assert a.build_scopes(PINNED) == PINNED  # AC-01
    with pytest.raises(OAuthAdapterError):
        a.build_scopes(frozenset({"https://www.googleapis.com/auth/gmail.modify"}))


def test_scope_broadening_requires_consent() -> None:
    a = _adapter()
    broad = frozenset({"https://www.googleapis.com/auth/contacts"})  # write scope
    with pytest.raises(OAuthAdapterError):  # AC-05
        a.request_scope_broadening(broad, consent_present=False)
    a.request_scope_broadening(broad, consent_present=True)  # allowed with recorded consent


def test_refresh_rotation_and_replay_revokes_family() -> None:
    mgr = RefreshTokenManager()
    t0 = mgr.issue_family()
    t1 = mgr.rotate(t0)
    assert t1 != t0
    with pytest.raises(RefreshReplayError):  # AC-02 replay of t0 (already used)
        mgr.rotate(t0)
    assert mgr.is_revoked(t1) is True  # whole family revoked


def test_token_encrypted_at_rest_under_adapter_partition() -> None:
    a = _adapter()
    ct = a.store_token(b"refresh-secret", object_ref="tok-1")  # AC-03
    assert ct != b"refresh-secret"
    assert a.load_token(ct, object_ref="tok-1") == b"refresh-secret"


def test_adapter_cannot_decrypt_other_providers_tokens() -> None:
    # AC-04 / partition: an adapter for a different provider cannot read these tokens.
    a = _adapter()
    ct = a.store_token(b"secret", object_ref="tok-1")
    other = OAuthAdapter("microsoft-graph", "microsoft", PINNED, a.secure_store,
                         RefreshTokenManager())
    from pingpals_api.persistence.secure_store import DecryptDenied

    with pytest.raises(DecryptDenied):
        other.load_token(ct, object_ref="tok-1")
