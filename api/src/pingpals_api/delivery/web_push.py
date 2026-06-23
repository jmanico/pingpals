"""Web-push adapter: VAPID auth + RFC 8291 message encryption (issue 051, FR-5.6/6.5).

In-app/push uses standard Web Push with the application's OWN VAPID keys and RFC 8291 message-level
payload encryption to the subscription keys, so an intermediary that terminates TLS can neither
read nor alter the message. A subscription that lacks the keys needed for message-level encryption
FAILS CLOSED (no push) — transport TLS alone is insufficient. Any outreach link carried in the
payload passes the FR-6.4 allowlist validator on render.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..outreach.links import validate_and_sanitize_url
from .payload import ChannelSurface, ReminderPayload


class WebPushError(Exception):
    """Push could not be sent with message-level protection — fail closed (no delivery)."""


@dataclass(frozen=True)
class PushSubscription:
    endpoint: str
    p256dh_key: str | None   # subscription public key (RFC 8291)
    auth_secret: str | None  # subscription auth secret (RFC 8291)

    def can_encrypt(self) -> bool:
        return bool(self.p256dh_key and self.auth_secret)


@dataclass(frozen=True)
class EncryptedPush:
    endpoint: str
    vapid_authorization: str
    ciphertext: bytes
    encrypted: bool = True


class WebPushAdapter:
    def __init__(
        self,
        vapid_sign: Callable[[str], str],
        encrypt_message: Callable[[PushSubscription, bytes], bytes],
    ) -> None:
        self._vapid_sign = vapid_sign            # produces the VAPID Authorization header
        self._encrypt_message = encrypt_message  # RFC 8291 ECE encryption (crypto behind interface)

    def send(self, subscription: PushSubscription, payload: ReminderPayload) -> EncryptedPush:
        if not subscription.can_encrypt():
            # No message-level protection possible -> fail closed (AC-04 / FR-6.5).
            raise WebPushError("subscription lacks RFC 8291 keys; refusing TLS-only push")

        # Sanitize any outreach link before it enters the payload (AC-05 / FR-6.4).
        action = validate_and_sanitize_url(payload.outreach_action) if payload.outreach_action \
            else None
        body = self._serialize(payload, action)
        ciphertext = self._encrypt_message(subscription, body)  # PII only inside the encrypted body
        authorization = self._vapid_sign(subscription.endpoint)
        return EncryptedPush(subscription.endpoint, authorization, ciphertext)

    @staticmethod
    def _serialize(payload: ReminderPayload, action: str | None) -> bytes:
        # On an untrusted surface only the opaque id is present (no PII); on the encrypted-body
        # surface the display name is included but ends up only inside the ciphertext (AC-03).
        if payload.surface is ChannelSurface.UNTRUSTED:
            return f"reminder={payload.reminder_id}".encode()
        body = f"reminder={payload.reminder_id};name={payload.display_name};action={action}"
        return body.encode()
