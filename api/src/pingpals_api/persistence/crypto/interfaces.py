"""Crypto / key-store interface contracts (REQ-FND-006, SEC-3.1, SEC-5.2, SEC-5.3).

Application code MUST NOT hold raw key material. All key operations are performed *behind* a
``KeyStore`` by a managed key store (the concrete vendor is `TO BE DECIDED` — DECISION 072 — so
the default binding fails closed). Callers never name an algorithm or a key directly: they call
the purpose-scoped ``CryptoService`` (see ``agility``), which resolves the configured algorithm
and key reference. This indirection is what makes rotation caller-transparent (SEC-5.3).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


class CryptoError(Exception):
    """Base class for all crypto-substrate failures."""


class CryptoUnavailableError(CryptoError):
    """The configured algorithm or key reference cannot be resolved or trusted.

    Per SEC-2.3 / NFR-1.6 the operation MUST fail closed (deny) rather than fall back to a weaker
    or default algorithm. Raised whenever an algorithm id is unregistered, a key reference is
    unresolved, or the key store is the default deny-all binding.
    """


@runtime_checkable
class Aead(Protocol):
    """An authenticated-encryption-with-associated-data primitive (e.g. AES-256-GCM).

    Implementations operate on a raw data key supplied by the ``KeyStore``; they never source or
    persist key material themselves.
    """

    #: Stable algorithm identifier recorded in the cryptographic inventory (SEC-5.5).
    algorithm_id: str
    #: Key length in bits, asserted against the supplied data key (e.g. 256 for AES-256-GCM).
    key_length_bits: int

    def encrypt(self, key: bytes, plaintext: bytes, associated_data: bytes | None) -> bytes:
        """Return ciphertext (nonce-prefixed, tag-appended). MUST be an authenticated cipher."""

    def decrypt(self, key: bytes, ciphertext: bytes, associated_data: bytes | None) -> bytes:
        """Return plaintext or raise ``CryptoError`` on any authentication failure (fail closed)."""


@runtime_checkable
class KeyStore(Protocol):
    """Managed key store: resolves a key *reference* to operations, never exposes raw keys.

    The default binding is the deny-all key store (``agility.DENY_ALL``) because the KMS vendor is
    undecided (SEC-3.1, DECISION 072). Decrypt/unwrap authority is least-privilege and partitioned
    per purpose/adapter (SECURITY.md §5); every invocation and denial is auditable (SEC-8.1).
    """

    def data_key(self, key_reference: str) -> bytes:
        """Resolve/unwrap the data key for ``key_reference``.

        Raises ``CryptoUnavailableError`` if the reference is unknown, the caller lacks the
        purpose-scoped grant, or the store is unavailable. MUST NOT return a default key.
        """
