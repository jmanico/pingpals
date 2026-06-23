"""Account / provider-identity linking with fresh re-auth + session binding (issue 034, INT-1.10).

Linking a provider identity or integration token is account-mutating, so it requires a FRESH
re-authentication by the session user before commit, and the resulting identity/token is bound
ONLY to the user of the SAME session that initiated the authorization request (per-session
state/PKCE binding). A callback completed in, or replayed into, a different session, or one lacking
the fresh re-auth, fails closed and links nothing.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass


class LinkingError(Exception):
    """Account-linking verification failed — fail closed, link nothing."""


@dataclass(frozen=True)
class LinkTransaction:
    state: str
    initiating_session_id: str
    user_id: str
    reauth_verified: bool


class LinkingCeremony:
    """Single-use, session-bound linking transactions."""

    def __init__(self) -> None:
        self._pending: dict[str, LinkTransaction] = {}

    def begin(self, session_id: str, user_id: str, reauth_verified: bool) -> LinkTransaction:
        if not session_id or not user_id:
            raise LinkingError("an authenticated session is required to link")
        if not reauth_verified:
            raise LinkingError("a fresh re-authentication is required before linking")  # AC-01
        txn = LinkTransaction(secrets.token_urlsafe(32), session_id, user_id, reauth_verified)
        self._pending[txn.state] = txn
        return txn

    def complete(self, state: str, callback_session_id: str) -> str:
        """Consume the transaction and return the user id to link, or fail closed (AC-02..AC-04)."""
        txn = self._pending.pop(state, None)  # single use: replay finds nothing
        if txn is None:
            raise LinkingError("unknown, replayed, or already-consumed linking transaction")
        if txn.initiating_session_id != callback_session_id:
            # callback completed in / replayed into a different session (AC-03)
            raise LinkingError("callback session does not match the initiating session")
        if not txn.reauth_verified:
            raise LinkingError("missing fresh re-auth")
        return txn.user_id
