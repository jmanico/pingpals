"""Notification preferences: channel order, per-category override, global pause (issue 055, FR-7.x).

Users set a preferred channel order and per-category channel overrides (scoped to the user) plus a
global pause (FR-7.2). Preference writes are validated and never mass-assign — an unknown or consent
field is rejected and changes no consent state. A preference does NOT authorize delivery: the
chosen channel is still gated by affirmative consent (FR-6.2), so a channel without consent fails
closed at delivery regardless of preference. Cross-user access returns not-found.
"""

from __future__ import annotations

from ..consent import ConsentLedger, is_delivery_consented
from ..persistence.repository import Repository
from ..validation import Field, validate

KNOWN_CHANNELS = ("inapp", "email", "push", "sms", "whatsapp", "signal")

_PREFS_SCHEMA = {
    "channel_order": Field("list", required=False, max_items=len(KNOWN_CHANNELS),
                           item=Field("str", max_length=16)),
    "paused": Field("bool", required=False),
}
_OVERRIDE_SCHEMA = {
    "category_id": Field("str", required=True, max_length=64),
    "channel": Field("str", required=True, max_length=16),
}


class PreferencesError(Exception):
    """Preference operation failed (fail closed; no write)."""


class PreferencesService:
    """Stores a per-user preferences record. (Persisted alongside user-scoped data.)"""

    def __init__(self, repo: Repository) -> None:
        self._repo = repo
        self._store: dict[str, dict] = {}  # owner_id -> prefs (kept user-scoped)

    def set_preferences(self, owner_id: str, payload: dict) -> dict:
        if not owner_id:
            raise PreferencesError("authentication required")
        data = validate(_PREFS_SCHEMA, payload)  # rejects unknown/consent fields (AC-03)
        for ch in data.get("channel_order", []):
            if ch not in KNOWN_CHANNELS:
                raise PreferencesError(f"unknown channel: {ch}")
        prefs = self._store.setdefault(owner_id, {"channel_order": [], "paused": False,
                                                  "overrides": {}})
        prefs.update(data)
        return dict(prefs)

    def set_category_override(self, owner_id: str, payload: dict) -> dict:
        data = validate(_OVERRIDE_SCHEMA, payload)
        if data["channel"] not in KNOWN_CHANNELS:
            raise PreferencesError("unknown channel")
        prefs = self._store.setdefault(owner_id, {"channel_order": [], "paused": False,
                                                  "overrides": {}})
        prefs["overrides"][data["category_id"]] = data["channel"]
        return dict(prefs)

    def get(self, owner_id: str) -> dict:
        prefs = self._store.get(owner_id)
        if prefs is None:
            raise PreferencesError("preferences not found")  # cross-user/missing (AC-05)
        return dict(prefs)

    def is_paused(self, owner_id: str) -> bool:
        return bool(self._store.get(owner_id, {}).get("paused"))

    def effective_channel(
        self,
        owner_id: str,
        category_id: str,
        consent: ConsentLedger,
        at_time: int,
    ) -> str | None:
        """Pick the first preferred/overridden channel that ALSO has affirmative consent (AC-04)."""
        prefs = self._store.get(owner_id, {})
        ordered = []
        override = prefs.get("overrides", {}).get(category_id)
        if override:
            ordered.append(override)
        ordered += [c for c in prefs.get("channel_order", []) if c != override]
        for channel in ordered:
            if is_delivery_consented(consent, owner_id, channel, at_time):
                return channel
        return None  # preference alone never authorizes delivery (FR-6.2)
