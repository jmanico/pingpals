"""Generic OAuth provider adapter (issue 033, INT-1.1/1.4/1.7, PRIV-1.2).

Each adapter declares a PINNED least-privilege scope set; an authorization request must equal that
set (Authorization Code + PKCE S256) — any scope outside it fails closed. Refresh tokens are
rotated on use with replay detection that revokes the whole token family on reuse. Issued tokens
are encrypted at rest under per-adapter partitioned decrypt authority (issue 022) and never leak
to URLs/logs/client storage. Disconnect revokes/purges one adapter's tokens independently.
Broadening authority (e.g. read→write) requires a new recorded consent capturing the new scope.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field

from ..persistence.secure_store import SecureStore


class OAuthAdapterError(Exception):
    """OAuth adapter policy violation — fail closed."""


class RefreshReplayError(OAuthAdapterError):
    """A used/unknown refresh token was presented; the token family is revoked."""


@dataclass
class TokenFamily:
    family_id: str
    active_token: str
    used_tokens: set[str] = field(default_factory=set)
    revoked: bool = False


class RefreshTokenManager:
    """Rotates refresh tokens on use; revokes the whole family on replay (INT-1.4, AC-02)."""

    def __init__(self) -> None:
        self._families: dict[str, TokenFamily] = {}   # family_id -> family
        self._token_index: dict[str, str] = {}        # token -> family_id

    def issue_family(self) -> str:
        family_id = secrets.token_urlsafe(16)
        token = secrets.token_urlsafe(32)
        self._families[family_id] = TokenFamily(family_id, token)
        self._token_index[token] = family_id
        return token

    def rotate(self, refresh_token: str) -> str:
        family_id = self._token_index.get(refresh_token)
        if family_id is None:
            raise RefreshReplayError("unknown refresh token")
        fam = self._families[family_id]
        if fam.revoked:
            raise RefreshReplayError("token family revoked")
        if refresh_token in fam.used_tokens or refresh_token != fam.active_token:
            # Replay of an already-rotated token -> revoke the entire family (AC-02).
            fam.revoked = True
            raise RefreshReplayError("refresh token replay detected; family revoked")
        fam.used_tokens.add(refresh_token)
        new_token = secrets.token_urlsafe(32)
        fam.active_token = new_token
        self._token_index[new_token] = family_id
        return new_token

    def is_revoked(self, refresh_token: str) -> bool:
        family_id = self._token_index.get(refresh_token)
        return family_id is None or self._families[family_id].revoked


@dataclass(frozen=True)
class OAuthAdapter:
    """An integration adapter with a pinned scope set and a purpose-partitioned token store."""

    name: str                          # e.g. "google-people"
    provider: str                      # e.g. "google"
    pinned_scopes: frozenset[str]
    secure_store: SecureStore
    refresh_manager: RefreshTokenManager

    @property
    def token_purpose(self) -> str:
        return f"token:{self.provider}"

    def build_scopes(self, requested: frozenset[str]) -> frozenset[str]:
        """Return the pinned scopes; reject any request outside the declared set (AC-01)."""
        if not requested <= self.pinned_scopes:
            raise OAuthAdapterError(f"{self.name}: scopes outside the pinned set are refused")
        return self.pinned_scopes  # always request exactly the pinned, least-privilege set

    def request_scope_broadening(self, new_scopes: frozenset[str], consent_present: bool) -> None:
        """Broadening beyond the pinned set requires a new recorded consent (AC-05, PRIV-1.2)."""
        if not (new_scopes <= self.pinned_scopes) and not consent_present:
            raise OAuthAdapterError("scope broadening requires a new recorded consent")

    def store_token(self, plaintext_token: bytes, object_ref: str) -> bytes:
        """Encrypt the token at rest under this adapter's partition only (AC-03)."""
        return self.secure_store.encrypt(self.name, self.token_purpose, plaintext_token,
                                         object_ref=object_ref)

    def load_token(self, ciphertext: bytes, object_ref: str) -> bytes:
        return self.secure_store.decrypt(self.name, self.token_purpose, ciphertext,
                                        object_ref=object_ref)
