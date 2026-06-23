"""Delivery-endpoint registration & lifecycle (issue 048, FR-6.5, SEC-2.2).

Every endpoint (email address, web-push subscription, …) is registered only within an authenticated
session, verified by proof of control, and bound to exactly one owning user before it may receive
any reminder. Registering/replacing/removing requires the authenticated owning user; no
unauthenticated or cross-user path exists. Endpoints are revoked/purged on logout, consent
withdrawal, and erasure. Before each delivery the worker confirms ownership and fails closed if it
cannot.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, replace


class EndpointError(Exception):
    """Endpoint lifecycle violation — fail closed; no state change."""


@dataclass(frozen=True)
class DeliveryEndpoint:
    id: str
    owner_id: str
    channel: str
    address: str
    verified: bool
    revoked: bool


class EndpointRegistry:
    def __init__(self) -> None:
        self._endpoints: dict[str, DeliveryEndpoint] = {}
        self._proofs: dict[str, str] = {}  # endpoint_id -> proof-of-control challenge

    def register(self, owner_id: str, channel: str, address: str) -> tuple[DeliveryEndpoint, str]:
        """Register (within an authenticated session) and return the endpoint + proof challenge."""
        if not owner_id:
            raise EndpointError("authentication required to register an endpoint")  # AC-06
        ep = DeliveryEndpoint(uuid.uuid4().hex, owner_id, channel, address, verified=False,
                              revoked=False)
        challenge = secrets.token_urlsafe(24)
        self._endpoints[ep.id] = ep
        self._proofs[ep.id] = challenge
        return ep, challenge

    def confirm(self, owner_id: str, endpoint_id: str, proof: str) -> DeliveryEndpoint:
        ep = self._owned(owner_id, endpoint_id)
        expected = self._proofs.get(endpoint_id)
        if expected is None or not secrets.compare_digest(expected, proof):
            raise EndpointError("proof of control failed")  # AC-01 verification required
        verified = replace(ep, verified=True)
        self._endpoints[endpoint_id] = verified
        del self._proofs[endpoint_id]
        return verified

    def revoke(self, owner_id: str, endpoint_id: str) -> None:
        ep = self._owned(owner_id, endpoint_id)
        self._endpoints[endpoint_id] = replace(ep, revoked=True)  # AC-05

    def revoke_all_for_user(self, owner_id: str) -> int:
        """Used on logout / erasure (FR-6.5, PRIV-1.6)."""
        victims = [e for e in self._endpoints.values() if e.owner_id == owner_id and not e.revoked]
        for e in victims:
            self._endpoints[e.id] = replace(e, revoked=True)
        return len(victims)

    def revoke_channel_for_user(self, owner_id: str, channel: str) -> int:
        """Used on per-channel consent withdrawal (FR-6.5)."""
        victims = [e for e in self._endpoints.values()
                   if e.owner_id == owner_id and e.channel == channel and not e.revoked]
        for e in victims:
            self._endpoints[e.id] = replace(e, revoked=True)
        return len(victims)

    def eligible(self, owner_id: str, channel: str) -> DeliveryEndpoint | None:
        """Return a verified, non-revoked endpoint owned by ``owner_id`` for ``channel`` or None."""
        for e in self._endpoints.values():
            if (e.owner_id == owner_id and e.channel == channel and e.verified
                    and not e.revoked):
                return e
        return None  # AC-02/AC-03: unverified/cross-user/missing -> not eligible

    def owns(self, owner_id: str, endpoint_id: str) -> bool:
        ep = self._endpoints.get(endpoint_id)
        return ep is not None and ep.owner_id == owner_id and ep.verified and not ep.revoked

    def _owned(self, owner_id: str, endpoint_id: str) -> DeliveryEndpoint:
        ep = self._endpoints.get(endpoint_id)
        if ep is None or ep.owner_id != owner_id:
            raise EndpointError("endpoint not found")  # cross-user/missing (AC-06)
        return ep
