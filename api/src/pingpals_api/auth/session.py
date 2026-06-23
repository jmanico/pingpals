"""Server-side session management (issue 030, SEC-1.2/1.3, SECURITY.md §2).

Sessions live in HttpOnly/Secure/SameSite cookies (set at the boundary); the id is never in
script-accessible storage. Sessions have idle AND absolute lifetimes and are server-revocable. A
fresh, unpredictable id is issued on every privilege transition (auth, MFA step-up, OIDC callback
promotion) and the prior session is invalidated — defeating fixation. If a fresh id cannot be
guaranteed, the transition fails closed (the session is denied, not reused).
"""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, replace

COOKIE_NAME = "pingpals_session"  # noqa: S105 — cookie name, not a secret


class SessionError(Exception):
    """Session establishment/validation failed — fail closed."""


@dataclass(frozen=True)
class Session:
    sid: str
    user_id: str | None      # None = anonymous (pre-auth) session
    created_at: float        # absolute-lifetime anchor
    last_seen: float         # idle-lifetime anchor
    authenticated: bool


class SessionManager:
    """In-memory session store (PostgreSQL-backed, revocable in production — behind this API)."""

    def __init__(
        self,
        idle_seconds: int = 1800,
        absolute_seconds: int = 43200,
        now: Callable[[], float] | None = None,
    ) -> None:
        self._idle = idle_seconds
        self._absolute = absolute_seconds
        self._now = now or time.time
        self._sessions: dict[str, Session] = {}

    @staticmethod
    def _new_sid() -> str:
        sid = secrets.token_urlsafe(32)
        if not sid:  # fail closed if a fresh id cannot be guaranteed (AC-05)
            raise SessionError("could not generate a fresh session id")
        return sid

    def begin_anonymous(self) -> Session:
        now = self._now()
        s = Session(self._new_sid(), None, now, now, authenticated=False)
        self._sessions[s.sid] = s
        return s

    def promote(self, prior_sid: str | None, user_id: str) -> Session:
        """Privilege transition: issue a FRESH id, invalidate the prior session (AC-03/AC-04)."""
        if prior_sid is not None:
            self._sessions.pop(prior_sid, None)  # old id can never be an authenticated session
        now = self._now()
        s = Session(self._new_sid(), user_id, now, now, authenticated=True)
        self._sessions[s.sid] = s
        return s

    def rotate(self, sid: str) -> Session:
        """Rotate the id of an existing authenticated session (e.g. after MFA step-up)."""
        current = self._sessions.get(sid)
        if current is None:
            raise SessionError("no such session to rotate")
        self._sessions.pop(sid, None)
        rotated = replace(current, sid=self._new_sid(), last_seen=self._now())
        self._sessions[rotated.sid] = rotated
        return rotated

    def validate(self, sid: str) -> Session | None:
        """Return the session if valid (not expired/revoked), refreshing idle; else None."""
        s = self._sessions.get(sid)
        if s is None:
            return None  # revoked or unknown
        now = self._now()
        if now - s.created_at > self._absolute or now - s.last_seen > self._idle:
            self._sessions.pop(sid, None)  # expired -> reject and drop
            return None
        refreshed = replace(s, last_seen=now)
        self._sessions[sid] = refreshed
        return refreshed

    def revoke(self, sid: str) -> bool:
        return self._sessions.pop(sid, None) is not None

    def revoke_all_for_user(self, user_id: str) -> int:
        victims = [sid for sid, s in self._sessions.items() if s.user_id == user_id]
        for sid in victims:
            del self._sessions[sid]
        return len(victims)


def apply_session_cookie(response, sid: str, secure: bool = True, max_age: int = 43200) -> None:
    """Set the session cookie with HttpOnly/Secure/SameSite (AC-01)."""
    response.set_cookie(
        COOKIE_NAME, sid,
        httponly=True, secure=secure, samesite="Lax", max_age=max_age, path="/",
    )
