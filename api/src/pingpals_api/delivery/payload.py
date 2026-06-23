"""Minimal / confidentiality-aware reminder payload (issue 047, FR-5.4/5.6, FR-6.5).

The payload carries only what is needed to act. Where a channel routes through a third-party
processor or renders on an untrusted surface (push body, lock screen), contact PII MUST NOT appear
in cleartext: either it is carried inside an RFC 8291 message-encrypted body, or the payload
references the reminder by an OPAQUE, non-guessable id resolvable only via an authenticated in-app
fetch. A push path that cannot apply message-level protection fails closed (no payload built).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ChannelSurface(str, Enum):
    AUTHENTICATED = "authenticated"     # in-app fetch over the user's session — PII allowed
    ENCRYPTED_BODY = "encrypted_body"   # RFC 8291 message encryption to the endpoint
    UNTRUSTED = "untrusted"             # push body / lock screen / unencryptable processor


class PayloadError(Exception):
    """A confidentiality-safe payload could not be built — fail closed (no send)."""


@dataclass(frozen=True)
class ReminderPayload:
    reminder_id: str            # opaque, non-guessable
    channel: str
    surface: ChannelSurface
    display_name: str | None    # present ONLY on authenticated / encrypted-body surfaces
    outreach_action: str | None
    encrypted: bool


def build_payload(
    reminder_id: str,
    channel: str,
    surface: ChannelSurface,
    display_name: str,
    outreach_action: str,
    *,
    can_encrypt_message: bool = False,
) -> ReminderPayload:
    """Build the smallest confidentiality-safe payload for the channel surface."""
    if surface is ChannelSurface.AUTHENTICATED:
        # In-app authenticated render: display name + action, no tokens/secrets (FR-5.4, AC-01).
        return ReminderPayload(reminder_id, channel, surface, display_name, outreach_action, False)

    if surface is ChannelSurface.ENCRYPTED_BODY:
        if not can_encrypt_message:
            # Push/processor path that cannot apply RFC 8291 protection -> fail closed (AC-07).
            raise PayloadError("message-level encryption unavailable; refusing to send PII")
        # PII only inside the encrypted body; the processor cannot read it (AC-03).
        return ReminderPayload(reminder_id, channel, surface, display_name, outreach_action, True)

    # UNTRUSTED surface: opaque id ONLY — no contact PII in cleartext (AC-02/AC-04).
    return ReminderPayload(reminder_id, channel, surface, None, None, False)


def contains_pii_cleartext(payload: ReminderPayload) -> bool:
    """True if the payload would expose contact PII in cleartext on the wire/surface."""
    if payload.surface is ChannelSurface.UNTRUSTED:
        return payload.display_name is not None or payload.outreach_action is not None
    if payload.surface is ChannelSurface.ENCRYPTED_BODY:
        return payload.display_name is not None and not payload.encrypted
    return False  # authenticated surface renders over the user's own session
