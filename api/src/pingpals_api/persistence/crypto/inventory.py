"""Cryptographic inventory (REQ-FND-006 AC-02, SEC-5.5).

A maintained registry of every crypto asset used to protect Restricted data, recording — per
SEC-5.5 — the algorithm, key length, key location/reference, and rotation status. This is the
record that rotation, audit, and breach response (PRIV-1.14) read from.

The inventory is Internal data and MUST NOT contain key material (only references/locations).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RotationStatus(str, Enum):
    """Lifecycle state of a key, for rotation tracking (SEC-5.5)."""

    ACTIVE = "active"          # current key for new encrypt operations
    RETIRING = "retiring"      # still valid for decrypt, not for new encrypt
    RETIRED = "retired"        # decommissioned; retained only for historical decrypt
    PENDING = "pending"        # provisioned, not yet promoted to active


@dataclass(frozen=True)
class CryptoAsset:
    """One inventoried cryptographic asset (SEC-5.5).

    All four SEC-5.5 fields are mandatory. ``key_location`` is a *reference* to where the managed
    key lives (e.g. a KMS key ARN/URI or key-store handle), never the key bytes.
    """

    name: str                       # purpose-scoped logical name, e.g. "at-rest:contact-pii"
    algorithm: str                  # e.g. "AES-256-GCM"
    key_length_bits: int            # e.g. 256
    key_location: str               # managed key-store reference; NEVER raw key material
    rotation_status: RotationStatus

    def __post_init__(self) -> None:
        if not self.key_location:
            raise ValueError("CryptoAsset.key_location is required (key reference, not material)")
        if self.key_length_bits <= 0:
            raise ValueError("CryptoAsset.key_length_bits must be positive")


class CryptoInventory:
    """Mutable collection of ``CryptoAsset`` records keyed by asset name."""

    def __init__(self) -> None:
        self._assets: dict[str, CryptoAsset] = {}

    def register(self, asset: CryptoAsset) -> None:
        self._assets[asset.name] = asset

    def get(self, name: str) -> CryptoAsset | None:
        return self._assets.get(name)

    def all(self) -> tuple[CryptoAsset, ...]:
        return tuple(self._assets.values())

    def __len__(self) -> int:
        return len(self._assets)

    def __contains__(self, name: object) -> bool:
        return name in self._assets
