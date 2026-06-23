"""OIDC ID-token validation + account binding (issue 029, INT-1.8/1.9, RFC 9068/OIDC Core).

The callback ID token is FULLY validated before any session is established: signature against the
provider JWKS (via an injected ``SignatureVerifier`` — the concrete JWKS fetch stays behind the
interface), then ``iss``, ``aud`` (= registered client id), ``exp``, ``iat``, and a single-use
``nonce`` bound to the initiating user agent (issue 028). The account is bound to the immutable
``(iss, sub)`` pair — never keyed/merged on a mutable email; email is a non-authoritative display
attribute used only when ``email_verified`` is true. Any failure fails closed: no session, no
cookie.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from .oidc import TransactionState


class IdTokenError(Exception):
    """ID-token validation failed — fail closed, establish no session."""


class SignatureVerifier(Protocol):
    def verify(self, id_token: str, expected_iss: str) -> dict:
        """Verify the JWT signature against the issuer's JWKS and return claims, or raise."""


@dataclass(frozen=True)
class AccountIdentity:
    """The immutable account key. Email is display-only (never an identity key)."""

    iss: str
    sub: str
    email: str | None  # only set when email_verified was true


def validate_id_token(
    id_token: str,
    txn: TransactionState,
    client_id: str,
    verifier: SignatureVerifier,
    ua_binding: str,
    now: Callable[[], float] | None = None,
    leeway: int = 60,
) -> AccountIdentity:
    """Validate the token end to end and resolve the account identity, or raise (AC-01..AC-05)."""
    clock = now or time.time

    # 1. Signature against the provider JWKS (raises on invalid/absent signature).
    claims = verifier.verify(id_token, txn.expected_iss)

    # 2. Standard claim checks — fail closed on any mismatch (AC-02).
    if claims.get("iss") != txn.expected_iss:
        raise IdTokenError("iss mismatch")
    if claims.get("aud") != client_id:
        raise IdTokenError("aud mismatch")  # aud MUST equal the registered client id
    nowt = clock()
    exp = claims.get("exp")
    iat = claims.get("iat")
    if not isinstance(exp, (int, float)) or nowt > exp + leeway:
        raise IdTokenError("token expired")
    if not isinstance(iat, (int, float)) or iat > nowt + leeway:
        raise IdTokenError("iat in the future")

    # 3. Single-use nonce bound to the initiating user agent (AC-02).
    if claims.get("nonce") != txn.nonce:
        raise IdTokenError("nonce mismatch")
    if txn.ua_binding != ua_binding:
        raise IdTokenError("user-agent binding mismatch")

    # 4. Account binding on immutable (iss, sub); email only if verified (AC-03/AC-05).
    sub = claims.get("sub")
    if not sub:
        raise IdTokenError("sub absent")  # identity resolution fails closed
    email = None
    raw_email = claims.get("email")
    if raw_email is not None:
        if claims.get("email_verified") is not True:
            raise IdTokenError("email not verified")  # never trust an unverified email
        email = raw_email

    return AccountIdentity(iss=txn.expected_iss, sub=str(sub), email=email)


def account_key(identity: AccountIdentity) -> tuple[str, str]:
    """The stable account key: (iss, sub). Email is intentionally excluded (AC-04)."""
    return (identity.iss, identity.sub)
