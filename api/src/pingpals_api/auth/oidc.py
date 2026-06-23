"""OIDC/OAuth initiation — Authorization Code + PKCE(S256) (issue 028, INT-1.1/1.2/1.3, RFC 9700).

Builds every authorization request with Authorization Code + PKCE ``S256`` and a fresh
``state``/``nonce``; the implicit and ROPC grants are refused. Each initiation persists a
single-use, short-lived transaction-state record (``state``/``code_verifier``/``nonce``/expected
``iss``) in a BOUNDED store that fails closed when full. Redirect URIs are matched by exact string
comparison against a preregistered allowlist. ID-token validation (issue 029) and session
promotion (issue 030) are separate.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass

DEFAULT_TTL_SECONDS = 300
DEFAULT_MAX_PENDING = 10_000


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def pkce_pair() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) using S256."""
    verifier = _b64url(secrets.token_bytes(48))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


class OidcError(Exception):
    """Base OIDC initiation error (all fail closed)."""


class StoreFullError(OidcError):
    """The bounded pending-transaction store is full; new initiations are refused."""


class TransactionNotFoundError(OidcError):
    """No matching pending transaction (consumed, expired, or never existed)."""


@dataclass(frozen=True)
class TransactionState:
    state: str
    code_verifier: str
    nonce: str
    expected_iss: str
    redirect_uri: str
    ua_binding: str          # binds the flow to the initiating user agent
    created_at: float


class TransactionStore:
    """Bounded, single-use, expiring store of pending authorization transactions."""

    def __init__(
        self,
        max_pending: int = DEFAULT_MAX_PENDING,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        now: Callable[[], float] | None = None,
    ) -> None:
        self._max = max_pending
        self._ttl = ttl_seconds
        self._now = now or time.time
        self._pending: dict[str, TransactionState] = {}

    def _evict_expired(self) -> None:
        cutoff = self._now() - self._ttl
        for state in [s for s, t in self._pending.items() if t.created_at < cutoff]:
            del self._pending[state]

    def put(self, txn: TransactionState) -> None:
        self._evict_expired()
        if len(self._pending) >= self._max:
            raise StoreFullError("pending-transaction store full")  # fail closed (AC-04)
        self._pending[txn.state] = txn

    def consume(self, state: str) -> TransactionState:
        """Return and DELETE the transaction for ``state``; reject if missing/expired (single-use)."""  # noqa: E501
        self._evict_expired()
        txn = self._pending.pop(state, None)
        if txn is None:
            raise TransactionNotFoundError(state)  # consumed, expired, or unknown (AC-03)
        return txn


@dataclass(frozen=True)
class OidcClientConfig:
    issuer: str
    client_id: str
    authorization_endpoint: str
    redirect_uri_allowlist: tuple[str, ...]
    scopes: tuple[str, ...] = ("openid", "email", "profile")


def is_allowed_redirect(config: OidcClientConfig, redirect_uri: str) -> bool:
    """Exact string match against the preregistered allowlist (INT-1.2, AC-02)."""
    return redirect_uri in config.redirect_uri_allowlist


@dataclass(frozen=True)
class AuthorizationRequest:
    url_params: dict[str, str]
    transaction: TransactionState


def build_authorization_request(
    config: OidcClientConfig,
    redirect_uri: str,
    ua_binding: str,
    store: TransactionStore,
    response_type: str = "code",
) -> AuthorizationRequest:
    """Build a code+PKCE authorization request and persist its transaction (AC-01)."""
    if response_type != "code":
        # no implicit / ROPC grant (AC-05)
        raise OidcError("only the authorization code grant is permitted")
    if not is_allowed_redirect(config, redirect_uri):
        raise OidcError("redirect_uri not in allowlist")

    verifier, challenge = pkce_pair()
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    txn = TransactionState(
        state=state, code_verifier=verifier, nonce=nonce, expected_iss=config.issuer,
        redirect_uri=redirect_uri, ua_binding=ua_binding, created_at=store._now(),
    )
    store.put(txn)  # may raise StoreFullError (fail closed)

    params = {
        "response_type": "code",
        "client_id": config.client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(config.scopes),
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return AuthorizationRequest(url_params=params, transaction=txn)
