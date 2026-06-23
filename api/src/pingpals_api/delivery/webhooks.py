"""Inbound webhook signature verification (SEC-7.1).

All inbound webhooks (SMS, WhatsApp, email provider) MUST verify the provider signature and reject
unsigned/invalid requests, with replay mitigation via a timestamp (or nonce) check. This is
distinct from internal east-west message authentication (issue 027). Verification fails closed.
"""

from __future__ import annotations

import hashlib
import hmac


class WebhookVerificationError(Exception):
    """The webhook signature/timestamp failed verification — reject (fail closed)."""


def compute_signature(secret: bytes, timestamp: int, body: bytes) -> str:
    mac = hmac.new(secret, f"{timestamp}.".encode() + body, hashlib.sha256)
    return mac.hexdigest()


def verify_webhook(
    secret: bytes,
    body: bytes,
    signature: str | None,
    timestamp: int,
    now: int,
    tolerance_seconds: int = 300,
) -> bool:
    """Return True only if the signature matches and the timestamp is within tolerance.

    Raises ``WebhookVerificationError`` on a missing/invalid signature or stale timestamp (replay).
    """
    if not signature:
        raise WebhookVerificationError("missing signature")  # unsigned -> reject
    if abs(now - timestamp) > tolerance_seconds:
        raise WebhookVerificationError("stale timestamp (replay window)")
    expected = compute_signature(secret, timestamp, body)
    if not hmac.compare_digest(expected, signature):
        raise WebhookVerificationError("signature mismatch")
    return True
