"""WebAuthn/passkey registration + assertion verification (issues 031/032, SEC-1.1, SECURITY §2).

Enforces the server-side verification policy that makes a passkey phishing-resistant MFA:
  * a fresh, server-generated, SINGLE-USE challenge bound to the in-flight ceremony;
  * RP ID and ``origin`` matched by EXACT string comparison;
  * user verification (UV) asserted for the factor to count;
  * a STRICTLY increasing signature counter (a non-increasing counter ⇒ cloned/replayed);
  * the assertion resolves to exactly ONE registered credential owned by the user;
  * registration only within an already-authenticated session, bound to the immutable user id.
Any failed check fails closed (rejects, never downgrades). The CBOR/COSE wire parsing and the raw
signature check are done by a vetted library at the edge and injected here as ``verify_signature``;
this module owns the policy. MFA step-up rotates the session via issue 030.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass


class WebAuthnError(Exception):
    """A WebAuthn ceremony failed verification — fail closed (no credential, no session)."""


@dataclass(frozen=True)
class RegisteredCredential:
    credential_id: str
    user_id: str
    public_key: bytes
    sign_count: int


@dataclass(frozen=True)
class RegistrationInput:
    user_id: str
    rp_id: str
    origin: str
    challenge: str
    credential_id: str
    public_key: bytes
    uv: bool
    sign_count: int


@dataclass(frozen=True)
class AssertionInput:
    user_id: str
    rp_id: str
    origin: str
    challenge: str
    credential_id: str
    uv: bool
    sign_count: int
    signature: bytes
    signed_data: bytes


class ChallengeStore:
    """Single-use challenges keyed by ceremony (user_id, purpose)."""

    def __init__(self) -> None:
        self._issued: dict[tuple[str, str], str] = {}

    def issue(self, user_id: str, purpose: str) -> str:
        challenge = secrets.token_urlsafe(32)
        self._issued[(user_id, purpose)] = challenge
        return challenge

    def consume(self, user_id: str, purpose: str, challenge: str) -> bool:
        key = (user_id, purpose)
        expected = self._issued.pop(key, None)  # single use: removed on consume
        return expected is not None and secrets.compare_digest(expected, challenge)


class CredentialStore:
    def __init__(self) -> None:
        self._by_id: dict[str, RegisteredCredential] = {}

    def add(self, cred: RegisteredCredential) -> None:
        self._by_id[cred.credential_id] = cred

    def resolve_for_user(self, credential_id: str, user_id: str) -> RegisteredCredential | None:
        cred = self._by_id.get(credential_id)
        if cred is None or cred.user_id != user_id:
            return None  # must resolve to exactly one credential owned by the user
        return cred

    def update_counter(self, credential_id: str, sign_count: int) -> None:
        cred = self._by_id[credential_id]
        self._by_id[credential_id] = RegisteredCredential(
            cred.credential_id, cred.user_id, cred.public_key, sign_count
        )


class WebAuthnRelyingParty:
    def __init__(
        self,
        rp_id: str,
        origin: str,
        challenges: ChallengeStore,
        credentials: CredentialStore,
        verify_signature: Callable[[bytes, bytes, bytes], bool] | None = None,
    ) -> None:
        self.rp_id = rp_id
        self.origin = origin
        self._challenges = challenges
        self._credentials = credentials
        # Default deny: without an injected verifier, no signature is ever accepted (fail closed).
        self._verify_signature = verify_signature or (lambda pk, sig, data: False)

    # ---- Registration (issue 031) ----
    def begin_registration(self, user_id: str, authenticated: bool) -> str:
        if not authenticated:
            raise WebAuthnError("registration requires an authenticated session")  # AC-03
        return self._challenges.issue(user_id, "register")

    def complete_registration(self, inp: RegistrationInput) -> RegisteredCredential:
        self._check_rp_and_origin(inp.rp_id, inp.origin)
        if not self._challenges.consume(inp.user_id, "register", inp.challenge):
            raise WebAuthnError("stale or reused challenge")  # AC-04
        if not inp.uv:
            raise WebAuthnError("user verification required")
        cred = RegisteredCredential(inp.credential_id, inp.user_id, inp.public_key, inp.sign_count)
        self._credentials.add(cred)  # bound to the session user's immutable id (AC-02)
        return cred

    # ---- Assertion / MFA step-up (issue 032) ----
    def verify_assertion(self, inp: AssertionInput) -> RegisteredCredential:
        self._check_rp_and_origin(inp.rp_id, inp.origin)
        if not self._challenges.consume(inp.user_id, "assert", inp.challenge):
            raise WebAuthnError("stale or reused challenge")  # AC-03
        if not inp.uv:
            raise WebAuthnError("user verification not asserted")  # AC-03
        cred = self._credentials.resolve_for_user(inp.credential_id, inp.user_id)
        if cred is None:
            raise WebAuthnError("assertion does not resolve to one owned credential")  # AC-04
        if inp.sign_count <= cred.sign_count:
            raise WebAuthnError("signature counter did not increase")  # cloned/replayed (AC-03)
        if not self._verify_signature(cred.public_key, inp.signature, inp.signed_data):
            raise WebAuthnError("signature verification failed")
        self._credentials.update_counter(cred.credential_id, inp.sign_count)
        return cred

    def begin_assertion(self, user_id: str) -> str:
        return self._challenges.issue(user_id, "assert")

    def _check_rp_and_origin(self, rp_id: str, origin: str) -> None:
        if rp_id != self.rp_id or origin != self.origin:  # exact string comparison
            raise WebAuthnError("RP ID / origin mismatch")
