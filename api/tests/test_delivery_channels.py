"""Email adapter + anti-spoofing + web push + preferences tests (issues 049/050/051/055)."""

from __future__ import annotations

import pytest

from pingpals_api.consent import ConsentEvent, InMemoryConsentLedger
from pingpals_api.delivery.email_adapter import EmailAdapter, EmailDeliveryFailed
from pingpals_api.delivery.email_authentication import (
    EmailAuthConfig,
    EmailAuthError,
    validate_email_auth,
)
from pingpals_api.delivery.payload import ChannelSurface, ReminderPayload
from pingpals_api.delivery.preferences import PreferencesError, PreferencesService
from pingpals_api.delivery.web_push import PushSubscription, WebPushAdapter, WebPushError
from pingpals_api.persistence.repository import InMemoryRepository
from pingpals_api.validation import ValidationError

PAYLOAD = ReminderPayload("r1", "email", ChannelSurface.AUTHENTICATED, "Alex", "mailto:a@x", False)


# ---- Email adapter (issue 049) ----

class _Provider:
    def __init__(self, response=None, raises=False):
        self.response = response
        self.raises = raises
        self.seen_credential = None

    def send(self, credential, to_address, payload):
        if self.raises:
            raise RuntimeError("smtp down")
        self.seen_credential = credential
        return self.response


def test_email_sends_and_uses_kms_credential_at_send_time() -> None:
    calls = []

    def cred():
        calls.append(1)
        return b"secret-api-key"

    provider = _Provider(response={"id": "msg-1", "accepted": True})
    out = EmailAdapter(provider, cred).send("a@x", PAYLOAD)  # AC-01
    assert out["id"] == "msg-1"
    assert calls == [1]  # credential fetched at send time (AC-02)


def test_email_malformed_response_is_not_delivered() -> None:
    provider = _Provider(response={"unexpected": True})
    with pytest.raises(EmailDeliveryFailed):  # AC-04
        EmailAdapter(provider, lambda: b"k").send("a@x", PAYLOAD)


def test_email_provider_error_is_not_delivered() -> None:
    with pytest.raises(EmailDeliveryFailed):  # AC-04
        EmailAdapter(_Provider(raises=True), lambda: b"k").send("a@x", PAYLOAD)


def test_email_rejected_flag_is_not_delivered() -> None:
    provider = _Provider(response={"id": "x", "accepted": False})
    with pytest.raises(EmailDeliveryFailed):
        EmailAdapter(provider, lambda: b"k").send("a@x", PAYLOAD)


# ---- Anti-spoofing (issue 050) ----

def _cfg(**over):
    base = dict(spf_record="v=spf1 include:_spf ~all", dkim_selector="s1",
               dkim_public_key="k", dkim_signing_enabled=True, dmarc_policy="reject",
               dmarc_aligned=True)
    base.update(over)
    return EmailAuthConfig(**base)


def test_reject_policy_with_alignment_passes() -> None:
    validate_email_auth(_cfg(), now=1000)  # AC-01/AC-02


def test_p_none_or_dkim_disabled_fails() -> None:
    with pytest.raises(EmailAuthError):  # AC-04
        validate_email_auth(_cfg(dmarc_policy="none"), now=1000)
    with pytest.raises(EmailAuthError):  # AC-05
        validate_email_auth(_cfg(dkim_signing_enabled=False), now=1000)
    with pytest.raises(EmailAuthError):
        validate_email_auth(_cfg(dmarc_aligned=False), now=1000)


def test_quarantine_only_with_future_expiry() -> None:
    with pytest.raises(EmailAuthError):
        validate_email_auth(_cfg(dmarc_policy="quarantine"), now=1000)  # no expiry
    validate_email_auth(_cfg(dmarc_policy="quarantine", quarantine_expiry_epoch=2000), now=1000)


# ---- Web push (issue 051) ----

def test_web_push_requires_rfc8291_keys_else_fails_closed() -> None:
    adapter = WebPushAdapter(vapid_sign=lambda ep: "vapid t=x", encrypt_message=lambda s, b: b"CT")
    no_keys = PushSubscription("https://push/endpoint", None, None)
    with pytest.raises(WebPushError):  # AC-04 fail closed (no TLS-only push)
        adapter.send(no_keys, PAYLOAD)


def test_web_push_encrypts_and_vapid_signs() -> None:
    seen = {}

    def encrypt(sub, body):
        seen["body"] = body
        return b"CIPHERTEXT"

    adapter = WebPushAdapter(vapid_sign=lambda ep: "vapid t=abc", encrypt_message=encrypt)
    sub = PushSubscription("https://push/endpoint", "p256", "auth")
    out = adapter.send(sub, PAYLOAD)  # AC-01
    assert out.ciphertext == b"CIPHERTEXT" and out.encrypted
    assert out.vapid_authorization == "vapid t=abc"


def test_web_push_untrusted_surface_has_no_pii_in_body() -> None:
    bodies = {}
    adapter = WebPushAdapter(lambda ep: "v", lambda s, b: bodies.setdefault("b", b) or b"CT")
    opaque = ReminderPayload("r9", "push", ChannelSurface.UNTRUSTED, None, None, False)
    adapter.send(PushSubscription("e", "p", "a"), opaque)
    assert b"name=" not in bodies["b"] and b"r9" in bodies["b"]  # AC-03


def test_web_push_sanitizes_outreach_link() -> None:
    bodies = {}
    adapter = WebPushAdapter(lambda ep: "v", lambda s, b: bodies.setdefault("b", b) or b"CT")
    evil = ReminderPayload("r1", "push", ChannelSurface.ENCRYPTED_BODY, "Alex",
                           "javascript:alert(1)", True)
    adapter.send(PushSubscription("e", "p", "a"), evil)
    assert b"javascript:" not in bodies["b"]  # AC-05 -> sanitized to "#"


# ---- Preferences (issue 055) ----

def _prefs():
    return PreferencesService(InMemoryRepository())


def test_set_and_get_preferences() -> None:
    svc = _prefs()
    svc.set_preferences("alice", {"channel_order": ["email", "push"], "paused": False})  # AC-01
    assert svc.get("alice")["channel_order"] == ["email", "push"]


def test_global_pause() -> None:
    svc = _prefs()
    svc.set_preferences("alice", {"paused": True})  # AC-02
    assert svc.is_paused("alice") is True


def test_unknown_or_consent_field_rejected() -> None:
    svc = _prefs()
    with pytest.raises(ValidationError):  # AC-03 no mass-assignment
        svc.set_preferences("alice", {"consent_email": True})


def test_cross_user_not_found() -> None:
    svc = _prefs()
    svc.set_preferences("alice", {"paused": True})
    with pytest.raises(PreferencesError):  # AC-05
        svc.get("bob")


def test_effective_channel_requires_consent() -> None:
    svc = _prefs()
    svc.set_preferences("alice", {"channel_order": ["email", "push"]})
    led = InMemoryConsentLedger()
    led.append(ConsentEvent("alice", "push", "grant", 1, "v1", 0))  # only push consented
    # AC-04: email is preferred first but lacks consent -> falls through to push.
    assert svc.effective_channel("alice", "cat1", led, 100) == "push"
    empty = InMemoryConsentLedger()
    assert svc.effective_channel("alice", "cat1", empty, 100) is None  # no consent -> no channel
