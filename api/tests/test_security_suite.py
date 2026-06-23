"""Security test suite (issue 077, TEST-1.3).

Consolidated coverage of the cross-cutting security cases: cross-user authorization isolation
(SEC-2.2), redirect-URI exact matching (INT-1.2), outreach URL scheme rejection (FR-6.4), token
non-exposure (INT-1.6), and webhook signature rejection (SEC-7.1).
"""

from __future__ import annotations

import os

import pytest

from pingpals_api.audit.sink import RecordingAuditSink
from pingpals_api.auth.oidc import OidcClientConfig, is_allowed_redirect
from pingpals_api.delivery.webhooks import (
    WebhookVerificationError,
    compute_signature,
    verify_webhook,
)
from pingpals_api.outreach.links import SAFE_FALLBACK, validate_and_sanitize_url
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


# TEST-1.3: cross-user authorization isolation (SEC-2.2)
def test_cross_user_isolation() -> None:
    repo = InMemoryRepository()
    repo.add("alice", "contact", "c1", {"display_name": "Alex"})
    assert repo.get("bob", "contact", "c1") is None
    assert repo.update("bob", "contact", "c1", {"display_name": "x"}) is None
    assert repo.delete("bob", "contact", "c1") is False


# TEST-1.3: redirect URI exact matching (INT-1.2)
def test_redirect_uri_exact_match() -> None:
    cfg = OidcClientConfig("iss", "cid", "https://auth", ("https://app.example/callback",))
    assert is_allowed_redirect(cfg, "https://app.example/callback") is True
    for bad in ["https://app.example/callback/", "https://app.example/callback?x=1",
                "https://app.example/callbackx", "https://evil.example/callback"]:
        assert is_allowed_redirect(cfg, bad) is False


# TEST-1.3: outreach URL scheme rejection (FR-6.4)
def test_outreach_scheme_rejection() -> None:
    assert validate_and_sanitize_url("javascript:alert(1)") == SAFE_FALLBACK
    assert validate_and_sanitize_url("data:text/html,x") == SAFE_FALLBACK
    assert validate_and_sanitize_url("https://wa.me.evil.example/1") == SAFE_FALLBACK
    assert validate_and_sanitize_url("mailto:a@x.com") == "mailto:a@x.com"


# TEST-1.3: token non-exposure (INT-1.6) — tokens stored encrypted; audit carries no plaintext
def test_token_non_exposure() -> None:
    reg = CryptoRegistry()
    reg.register(AesGcm256())

    class _K(KeyStore):
        def __init__(self):
            self.k = os.urandom(32)

        def data_key(self, ref):
            if ref != "kref":
                raise CryptoUnavailableError(ref)
            return self.k

    config = CryptoConfig({"token:google": PurposeBinding("AES-256-GCM", "kref")})
    crypto = CryptoService(reg, config, _K())
    audit = RecordingAuditSink()
    store = SecureStore(crypto, [Grant("google", frozenset({"token:google"}))], audit)
    secret = b"super-secret-refresh-token"
    ct = store.encrypt("google", "token:google", secret, object_ref="tok-1")
    assert secret not in ct  # stored as ciphertext
    for e in audit.events:  # no plaintext in any audit entry
        blob = e.action + e.principal + e.purpose + (e.object_ref or "")
        assert "super-secret" not in blob


# TEST-1.3: webhook signature rejection (SEC-7.1)
def test_webhook_signature_rejection() -> None:
    secret = b"provider-webhook-secret"
    body = b'{"event":"delivered"}'
    sig = compute_signature(secret, timestamp=1000, body=body)
    assert verify_webhook(secret, body, sig, timestamp=1000, now=1100) is True
    with pytest.raises(WebhookVerificationError):  # unsigned
        verify_webhook(secret, body, None, timestamp=1000, now=1100)
    with pytest.raises(WebhookVerificationError):  # tampered/invalid
        verify_webhook(secret, body, "deadbeef", timestamp=1000, now=1100)
    with pytest.raises(WebhookVerificationError):  # stale -> replay
        verify_webhook(secret, body, sig, timestamp=1000, now=100_000)
