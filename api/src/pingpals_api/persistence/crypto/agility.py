"""Crypto-agility layer (REQ-FND-006 AC-01, SEC-5.3).

Callers use the purpose-scoped ``CryptoService`` and never name an algorithm or a key. The active
algorithm and key reference for each *purpose* live in ``CryptoConfig`` and can be rotated without
any change to caller code (SEC-5.3). Resolution fails closed (``CryptoUnavailableError``) whenever
the purpose, algorithm, or key reference is unknown/unresolved, or the key store denies — never a
silent fallback to a weaker algorithm (SEC-2.3, NFR-1.6).

Default key store is ``DENY_ALL`` because the managed-KMS vendor is `TO BE DECIDED` (DECISION 072).
"""

from __future__ import annotations

from dataclasses import dataclass

from .interfaces import Aead, CryptoUnavailableError, KeyStore
from .inventory import CryptoAsset, CryptoInventory, RotationStatus


@dataclass(frozen=True)
class PurposeBinding:
    """Maps a Restricted-data *purpose* to its active algorithm and managed key reference."""

    algorithm_id: str
    key_reference: str
    rotation_status: RotationStatus = RotationStatus.ACTIVE


class CryptoConfig:
    """Purpose → :class:`PurposeBinding`. Mutable so bindings can be rotated at runtime/config."""

    def __init__(self, bindings: dict[str, PurposeBinding] | None = None) -> None:
        self._bindings: dict[str, PurposeBinding] = dict(bindings or {})

    def bind(self, purpose: str, binding: PurposeBinding) -> None:
        """Set or rotate the binding for ``purpose`` (caller-transparent — SEC-5.3)."""
        self._bindings[purpose] = binding

    def resolve(self, purpose: str) -> PurposeBinding:
        binding = self._bindings.get(purpose)
        if binding is None:
            raise CryptoUnavailableError(f"no crypto binding configured for purpose {purpose!r}")
        return binding

    def purposes(self) -> tuple[str, ...]:
        return tuple(self._bindings)


class CryptoRegistry:
    """Algorithm id → :class:`Aead` provider. New algorithms register without caller changes."""

    def __init__(self) -> None:
        self._providers: dict[str, Aead] = {}

    def register(self, provider: Aead) -> None:
        self._providers[provider.algorithm_id] = provider

    def resolve(self, algorithm_id: str) -> Aead:
        provider = self._providers.get(algorithm_id)
        if provider is None:
            raise CryptoUnavailableError(f"crypto algorithm {algorithm_id!r} is not registered")
        return provider


class DenyAllKeyStore(KeyStore):
    """Default fail-closed key store: resolves no key (SEC-3.1, DECISION 072 unresolved)."""

    def data_key(self, key_reference: str) -> bytes:
        raise CryptoUnavailableError(
            "no managed key store is configured (KMS vendor TO BE DECIDED); key resolution denied"
        )


#: Process-wide default binding until a managed KMS is wired in.
DENY_ALL: KeyStore = DenyAllKeyStore()


class CryptoService:
    """Purpose-scoped encrypt/decrypt facade — the only crypto surface callers depend on.

    Rotating the algorithm or key reference for a purpose (via ``CryptoConfig.bind``) requires no
    change to any caller (REQ-FND-006 AC-01 / SEC-5.3).
    """

    def __init__(
        self,
        registry: CryptoRegistry,
        config: CryptoConfig,
        key_store: KeyStore = DENY_ALL,
    ) -> None:
        self._registry = registry
        self._config = config
        self._key_store = key_store

    def encrypt(
        self, purpose: str, plaintext: bytes, associated_data: bytes | None = None
    ) -> bytes:
        binding = self._config.resolve(purpose)
        aead = self._registry.resolve(binding.algorithm_id)
        key = self._key_store.data_key(binding.key_reference)  # raises -> fail closed
        return aead.encrypt(key, plaintext, associated_data)

    def decrypt(
        self, purpose: str, ciphertext: bytes, associated_data: bytes | None = None
    ) -> bytes:
        binding = self._config.resolve(purpose)
        aead = self._registry.resolve(binding.algorithm_id)
        key = self._key_store.data_key(binding.key_reference)  # raises -> fail closed
        return aead.decrypt(key, ciphertext, associated_data)

    def inventory(self) -> CryptoInventory:
        """Project the active configuration into a cryptographic inventory (SEC-5.5)."""
        inv = CryptoInventory()
        for purpose in self._config.purposes():
            binding = self._config.resolve(purpose)
            aead = self._registry.resolve(binding.algorithm_id)
            inv.register(
                CryptoAsset(
                    name=purpose,
                    algorithm=aead.algorithm_id,
                    key_length_bits=aead.key_length_bits,
                    key_location=binding.key_reference,
                    rotation_status=binding.rotation_status,
                )
            )
        return inv
