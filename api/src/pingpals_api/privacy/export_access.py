"""Export-artifact access control (issue 058, PRIV-1.17).

The export artifact is Restricted data. Download requires the owner's authenticated session OR a
short-lived, SINGLE-USE, unguessable token; it expires, is non-enumerable, and is denied for any
unauthenticated/expired/already-used/non-owner request. Artifacts are deleted on a bounded
retention schedule and on the owner's erasure.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass


class ExportAccessDenied(Exception):
    """Download denied (unauthenticated/expired/used/non-owner) — no bytes served."""


@dataclass
class _Artifact:
    owner_id: str
    content: bytes
    token: str
    expires_at: int
    used: bool = False


class ExportArtifactStore:
    def __init__(self, ttl_seconds: int = 900, now: Callable[[], int] | None = None) -> None:
        self._ttl = ttl_seconds
        self._now = now or (lambda: 0)
        self._by_id: dict[str, _Artifact] = {}

    def put(self, owner_id: str, content: bytes) -> tuple[str, str]:
        """Store an artifact; return (unguessable artifact id, single-use download token)."""
        artifact_id = secrets.token_urlsafe(24)
        token = secrets.token_urlsafe(32)
        self._by_id[artifact_id] = _Artifact(owner_id, content, token,
                                             self._now() + self._ttl)
        return artifact_id, token

    def download(self, artifact_id: str, owner_id: str, token: str) -> bytes:
        art = self._by_id.get(artifact_id)
        # Non-owner / unknown id -> not-found, no disclosure (AC-01/AC-05).
        if art is None or art.owner_id != owner_id:
            raise ExportAccessDenied("not found")
        if art.used:
            raise ExportAccessDenied("token already used")          # AC-04 single-use
        if self._now() > art.expires_at:
            del self._by_id[artifact_id]
            raise ExportAccessDenied("expired")                     # AC-04 time-bounded
        if not secrets.compare_digest(art.token, token):
            raise ExportAccessDenied("invalid token")
        art.used = True
        content = art.content
        del self._by_id[artifact_id]  # consumed
        return content

    def purge_expired(self) -> int:
        now = self._now()
        victims = [aid for aid, a in self._by_id.items() if now > a.expires_at]
        for aid in victims:
            del self._by_id[aid]
        return len(victims)

    def purge_for_owner(self, owner_id: str) -> int:
        """Delete all artifacts for a user on erasure (AC-02, PRIV-1.6)."""
        victims = [aid for aid, a in self._by_id.items() if a.owner_id == owner_id]
        for aid in victims:
            del self._by_id[aid]
        return len(victims)
