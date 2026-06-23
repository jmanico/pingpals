"""Crypto-agility substrate and cryptographic inventory (REQ-FND-006).

Public surface for the rest of the API. Callers depend only on ``CryptoService`` (purpose-scoped)
and the inventory types — never on a concrete algorithm or key. Default key store fails closed
because the managed-KMS vendor is `TO BE DECIDED` (SEC-3.1, DECISION 072).
"""

from .agility import (
    DENY_ALL,
    CryptoConfig,
    CryptoRegistry,
    CryptoService,
    DenyAllKeyStore,
    PurposeBinding,
)
from .interfaces import Aead, CryptoError, CryptoUnavailableError, KeyStore
from .inventory import CryptoAsset, CryptoInventory, RotationStatus
from .providers import AesGcm256

__all__ = [
    "Aead",
    "AesGcm256",
    "CryptoAsset",
    "CryptoConfig",
    "CryptoError",
    "CryptoInventory",
    "CryptoRegistry",
    "CryptoService",
    "CryptoUnavailableError",
    "DENY_ALL",
    "DenyAllKeyStore",
    "KeyStore",
    "PurposeBinding",
    "RotationStatus",
]
