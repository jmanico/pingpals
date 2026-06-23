"""At-rest encryption envelope with partitioned, audited decrypt authority (issue 022).

Restricted data is encrypted with AES-256-GCM under managed keys via the crypto-agility layer
(issue 006); application code never holds raw key material. The right to decrypt is itself a
sensitive grant, so it is partitioned: each component/adapter may decrypt ONLY the purposes
(data classes / provider tokens) it is explicitly granted. There is no application-wide decrypt
role; any principal without a grant is denied by default (SEC-3.1, SECURITY.md §5, ARCH Rule 7).
Every decrypt/encrypt invocation and every denial is recorded in the audit log, attributing the
caller and purpose and excluding plaintext (SEC-8.1/8.2).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ..audit.sink import AuditEvent, AuditSink
from .crypto import CryptoError, CryptoService


class DecryptDenied(CryptoError):
    """The calling component has no grant for the requested purpose (default deny)."""


@dataclass(frozen=True)
class Grant:
    """A component's least-privilege decrypt authority — only the listed purposes."""

    component: str
    purposes: frozenset[str]


class SecureStore:
    """Purpose-partitioned, audited at-rest envelope over :class:`CryptoService`."""

    def __init__(
        self,
        crypto: CryptoService,
        grants: Iterable[Grant],
        audit: AuditSink,
    ) -> None:
        self._crypto = crypto
        self._grants: dict[str, frozenset[str]] = {g.component: g.purposes for g in grants}
        self._audit = audit

    def _authorized(self, component: str, purpose: str) -> bool:
        return purpose in self._grants.get(component, frozenset())

    def _deny(self, action: str, component: str, purpose: str, object_ref: str | None) -> None:
        self._audit.record(AuditEvent(action, component, purpose, "denied", object_ref))

    def encrypt(
        self,
        component: str,
        purpose: str,
        plaintext: bytes,
        *,
        associated_data: bytes | None = None,
        object_ref: str | None = None,
    ) -> bytes:
        if not self._authorized(component, purpose):
            self._deny("crypto.encrypt.denied", component, purpose, object_ref)
            raise DecryptDenied(f"{component!r} not granted purpose {purpose!r}")
        ciphertext = self._crypto.encrypt(purpose, plaintext, associated_data)
        self._audit.record(AuditEvent("crypto.encrypt", component, purpose, "allowed", object_ref))
        return ciphertext

    def decrypt(
        self,
        component: str,
        purpose: str,
        ciphertext: bytes,
        *,
        associated_data: bytes | None = None,
        object_ref: str | None = None,
    ) -> bytes:
        if not self._authorized(component, purpose):
            self._deny("crypto.decrypt.denied", component, purpose, object_ref)
            raise DecryptDenied(f"{component!r} not granted purpose {purpose!r}")
        plaintext = self._crypto.decrypt(purpose, ciphertext, associated_data)
        self._audit.record(AuditEvent("crypto.decrypt", component, purpose, "allowed", object_ref))
        return plaintext

    def grants_all_purposes(self, all_purposes: Iterable[str]) -> bool:
        """True if ANY single component is granted every purpose — an app-wide role (forbidden)."""
        wanted = set(all_purposes)
        return any(wanted <= purposes for purposes in self._grants.values())
