"""Concrete crypto primitive providers (REQ-FND-006, SEC-5.2).

These operate only on a raw data key handed in by a ``KeyStore``; they never source, generate, or
persist key material. Adding a new algorithm here (and registering it in ``agility``) is how the
system stays crypto-agile (SEC-5.3) — callers are unaffected.
"""

from __future__ import annotations

import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .interfaces import Aead, CryptoError

_GCM_NONCE_BYTES = 12  # 96-bit nonce, the AES-GCM standard


class AesGcm256(Aead):
    """AES-256-GCM authenticated cipher (SEC-5.2).

    Wire format: ``nonce (12 bytes) || ciphertext || tag`` (the tag is appended by AESGCM).
    """

    algorithm_id = "AES-256-GCM"
    key_length_bits = 256

    def encrypt(self, key: bytes, plaintext: bytes, associated_data: bytes | None) -> bytes:
        self._check_key(key)
        nonce = os.urandom(_GCM_NONCE_BYTES)
        ct = AESGCM(key).encrypt(nonce, plaintext, associated_data)
        return nonce + ct

    def decrypt(self, key: bytes, ciphertext: bytes, associated_data: bytes | None) -> bytes:
        self._check_key(key)
        if len(ciphertext) < _GCM_NONCE_BYTES:
            raise CryptoError("ciphertext too short to contain a nonce")
        nonce, ct = ciphertext[:_GCM_NONCE_BYTES], ciphertext[_GCM_NONCE_BYTES:]
        try:
            return AESGCM(key).decrypt(nonce, ct, associated_data)
        except InvalidTag as exc:  # fail closed on any authentication failure
            raise CryptoError("AES-256-GCM authentication failed") from exc

    def _check_key(self, key: bytes) -> None:
        if len(key) * 8 != self.key_length_bits:
            raise CryptoError(
                f"{self.algorithm_id} requires a {self.key_length_bits}-bit key, "
                f"got {len(key) * 8} bits"
            )
