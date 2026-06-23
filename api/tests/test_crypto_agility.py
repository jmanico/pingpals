"""Crypto-agility + cryptographic-inventory tests (REQ-FND-006).

AC-01: rotating the configured algorithm or key reference for a purpose requires no caller change.
AC-02: the cryptographic inventory records algorithm, key length, key location, rotation status.
Plus the fail-closed invariant (SEC-2.3 / NFR-1.6): an unresolved algorithm/key/purpose, or the
default deny-all key store, denies the operation instead of returning plaintext.
"""

from __future__ import annotations

import os

import pytest

from pingpals_api.persistence.crypto import (
    DENY_ALL,
    AesGcm256,
    CryptoConfig,
    CryptoError,
    CryptoRegistry,
    CryptoService,
    CryptoUnavailableError,
    KeyStore,
    PurposeBinding,
    RotationStatus,
)


class InMemoryKeyStore(KeyStore):
    """DEV/TEST-ONLY key store. Production resolves keys through a managed KMS (DECISION 072)."""

    def __init__(self, keys: dict[str, bytes]) -> None:
        self._keys = dict(keys)

    def data_key(self, key_reference: str) -> bytes:
        try:
            return self._keys[key_reference]
        except KeyError as exc:
            raise CryptoUnavailableError(f"unknown key reference {key_reference!r}") from exc


class Aes128Gcm(AesGcm256):
    """A second registered algorithm, used only to prove caller-transparent rotation (AC-01)."""

    algorithm_id = "AES-128-GCM"
    key_length_bits = 128


def _registry() -> CryptoRegistry:
    reg = CryptoRegistry()
    reg.register(AesGcm256())
    reg.register(Aes128Gcm())
    return reg


# A caller that depends ONLY on CryptoService — never on an algorithm or key (SEC-5.3).
def _caller_roundtrip(service: CryptoService, purpose: str, msg: bytes) -> bytes:
    ct = service.encrypt(purpose, msg, associated_data=b"contact-record")
    return service.decrypt(purpose, ct, associated_data=b"contact-record")


def test_roundtrip_under_configured_binding() -> None:
    keys = {"kref-a": os.urandom(32)}
    service = CryptoService(_registry(), CryptoConfig(
        {"at-rest:contact-pii": PurposeBinding("AES-256-GCM", "kref-a")}
    ), InMemoryKeyStore(keys))
    assert _caller_roundtrip(service, "at-rest:contact-pii", b"secret notes") == b"secret notes"


def test_algorithm_rotation_is_caller_transparent() -> None:
    """AC-01: switch the purpose's algorithm + key; the SAME caller code keeps working."""
    keys = {"kref-256": os.urandom(32), "kref-128": os.urandom(16)}
    config = CryptoConfig({"at-rest:contact-pii": PurposeBinding("AES-256-GCM", "kref-256")})
    service = CryptoService(_registry(), config, InMemoryKeyStore(keys))
    assert _caller_roundtrip(service, "at-rest:contact-pii", b"v1") == b"v1"

    # Operator rotates algorithm + key reference — no caller signature changes.
    config.bind("at-rest:contact-pii", PurposeBinding("AES-128-GCM", "kref-128"))
    assert _caller_roundtrip(service, "at-rest:contact-pii", b"v2") == b"v2"


def test_fail_closed_on_default_deny_all_keystore() -> None:
    service = CryptoService(_registry(), CryptoConfig(
        {"at-rest:contact-pii": PurposeBinding("AES-256-GCM", "kref-a")}
    ), DENY_ALL)
    with pytest.raises(CryptoUnavailableError):
        service.encrypt("at-rest:contact-pii", b"x")


def test_fail_closed_on_unknown_purpose() -> None:
    service = CryptoService(_registry(), CryptoConfig(), InMemoryKeyStore({}))
    with pytest.raises(CryptoUnavailableError):
        service.encrypt("nope", b"x")


def test_fail_closed_on_unregistered_algorithm() -> None:
    service = CryptoService(_registry(), CryptoConfig(
        {"p": PurposeBinding("ROT13", "kref-a")}
    ), InMemoryKeyStore({"kref-a": os.urandom(32)}))
    with pytest.raises(CryptoUnavailableError):
        service.encrypt("p", b"x")


def test_tampered_ciphertext_fails_authentication() -> None:
    keys = {"kref-a": os.urandom(32)}
    service = CryptoService(_registry(), CryptoConfig(
        {"p": PurposeBinding("AES-256-GCM", "kref-a")}
    ), InMemoryKeyStore(keys))
    ct = bytearray(service.encrypt("p", b"hello", associated_data=b"ad"))
    ct[-1] ^= 0x01  # flip a tag bit
    with pytest.raises(CryptoError):
        service.decrypt("p", bytes(ct), associated_data=b"ad")


def test_inventory_records_all_sec_5_5_fields() -> None:
    """AC-02 / SEC-5.5: algorithm, key length, key location, rotation status are all recorded."""
    config = CryptoConfig({
        "at-rest:contact-pii": PurposeBinding(
            "AES-256-GCM", "kms://key/contact", RotationStatus.ACTIVE
        ),
        "audit:hash-key": PurposeBinding(
            "AES-256-GCM", "kms://key/audit", RotationStatus.RETIRING
        ),
    })
    service = CryptoService(_registry(), config, InMemoryKeyStore({}))
    inv = service.inventory()
    assert len(inv) == 2
    asset = inv.get("at-rest:contact-pii")
    assert asset is not None
    assert asset.algorithm == "AES-256-GCM"
    assert asset.key_length_bits == 256
    assert asset.key_location == "kms://key/contact"
    assert asset.rotation_status is RotationStatus.ACTIVE
    assert inv.get("audit:hash-key").rotation_status is RotationStatus.RETIRING
