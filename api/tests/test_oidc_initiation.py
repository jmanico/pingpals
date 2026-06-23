"""OIDC initiation tests (issue 028 / REQ-AUTH-017)."""

from __future__ import annotations

import base64
import hashlib

import pytest

from pingpals_api.auth.oidc import (
    OidcClientConfig,
    OidcError,
    StoreFullError,
    TransactionNotFoundError,
    TransactionStore,
    build_authorization_request,
    is_allowed_redirect,
)

CONFIG = OidcClientConfig(
    issuer="https://accounts.google.com",
    client_id="client-123",
    authorization_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
    redirect_uri_allowlist=("https://app.pingpals.example/callback",),
)
REDIRECT = "https://app.pingpals.example/callback"


class Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def test_builds_code_pkce_request_and_persists_txn() -> None:
    store = TransactionStore(now=Clock())
    req = build_authorization_request(CONFIG, REDIRECT, "ua-1", store)
    p = req.url_params
    assert p["response_type"] == "code"
    assert p["code_challenge_method"] == "S256"
    assert p["state"] and p["nonce"] and p["code_challenge"]  # AC-01
    # challenge is S256(verifier)
    expected = base64.urlsafe_b64encode(
        hashlib.sha256(req.transaction.code_verifier.encode()).digest()
    ).rstrip(b"=").decode()
    assert p["code_challenge"] == expected


def test_exact_redirect_match_only() -> None:
    assert is_allowed_redirect(CONFIG, REDIRECT) is True  # AC-02
    for bad in [
        REDIRECT + "/",
        REDIRECT + "?x=1",
        REDIRECT + "/sub",
        "https://app.pingpals.example/callbackx",
        "https://evil.example/callback",
    ]:
        assert is_allowed_redirect(CONFIG, bad) is False


def test_implicit_and_ropc_refused() -> None:
    store = TransactionStore(now=Clock())
    with pytest.raises(OidcError):  # AC-05
        build_authorization_request(CONFIG, REDIRECT, "ua-1", store, response_type="token")


def test_transaction_single_use_and_expiry() -> None:
    clock = Clock()
    store = TransactionStore(ttl_seconds=300, now=clock)
    req = build_authorization_request(CONFIG, REDIRECT, "ua-1", store)
    state = req.transaction.state
    assert store.consume(state).state == state  # first use ok
    with pytest.raises(TransactionNotFoundError):  # AC-03 replay
        store.consume(state)

    # expiry eviction
    req2 = build_authorization_request(CONFIG, REDIRECT, "ua-1", store)
    clock.t += 301
    with pytest.raises(TransactionNotFoundError):  # AC-03 expired
        store.consume(req2.transaction.state)


def test_store_bound_fails_closed() -> None:
    store = TransactionStore(max_pending=1, now=Clock())
    build_authorization_request(CONFIG, REDIRECT, "ua-1", store)
    with pytest.raises(StoreFullError):  # AC-04
        build_authorization_request(CONFIG, REDIRECT, "ua-2", store)
