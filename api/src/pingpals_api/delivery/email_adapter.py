"""Email delivery adapter (issue 049, INT-2.1, SEC-3.x).

Sends the minimal payload (036) via a transactional provider's authenticated API behind an
``EmailProvider`` interface (concrete provider deferred — DECISION). Provider credentials are
fetched from the KMS-backed store AT SEND TIME and never appear in source, config, images, logs, or
audit entries. A malformed/error provider response is validated and treated as NOT delivered, then
surfaced to retry/DLQ (issue 052) — never reported as success.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from ..validation import Field, ValidationError, validate
from .payload import ReminderPayload

_PROVIDER_RESPONSE = {
    "id": Field("str", required=True, max_length=200),
    "accepted": Field("bool", required=True),
}


class EmailDeliveryFailed(Exception):
    """The send did not succeed; surface to retry/DLQ (never report success)."""


class EmailProvider(Protocol):
    def send(self, credential: bytes, to_address: str, payload: ReminderPayload) -> dict:
        """Send via the provider's authenticated API and return its raw response dict."""


class EmailAdapter:
    def __init__(
        self,
        provider: EmailProvider,
        credential_provider: Callable[[], bytes],  # resolves from the KMS-backed store at send time
    ) -> None:
        self._provider = provider
        self._credential_provider = credential_provider

    def send(self, to_address: str, payload: ReminderPayload) -> dict:
        credential = self._credential_provider()  # never logged / never persisted in plaintext
        try:
            raw = self._provider.send(credential, to_address, payload)
        except Exception as exc:  # provider/transport error -> not delivered (AC-04)
            raise EmailDeliveryFailed("provider error") from exc
        finally:
            credential = b""  # drop the secret from local scope promptly

        try:
            response = validate(_PROVIDER_RESPONSE, raw)  # untrusted provider response (SEC-4.1)
        except ValidationError as exc:
            raise EmailDeliveryFailed("malformed provider response") from exc
        if not response["accepted"]:
            raise EmailDeliveryFailed("provider rejected the message")  # AC-04
        return response
