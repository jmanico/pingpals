"""Scheduler: cadence evaluation + idempotent reminder generation (issues 042/043, FR-5.1/5.2).

Generates exactly one reminder for a contact when ALL hold: now − last_contacted ≥ effective
cadence, the time is within the send window, channel consent is present, and no active snooze
exists. Generation is idempotent (an ``idempotency_key`` per contact-per-window) so re-running the
window produces no duplicates. Output is bounded by the contact quota and capped per user per
window (SEC-6.2); the cap is server-enforced and resets each window. Unknown timezone or
indeterminate consent fail closed (no reminder). A globally-paused account generates nothing.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..audit.log import TamperEvidentAuditLog
from ..consent import ConsentLedger, is_delivery_consented
from ..contacts.cadence import effective_cadence_days, is_delivery_allowed
from ..persistence.repository import Repository

_DAY_SECONDS = 86_400


@dataclass(frozen=True)
class UserSettings:
    timezone: str | None
    quiet_hours: tuple[int, int] | None
    channel: str
    paused: bool = False
    per_window_cap: int = 50


class Scheduler:
    def __init__(
        self,
        repo: Repository,
        audit: TamperEvidentAuditLog,
        consent: ConsentLedger,
    ) -> None:
        self._repo = repo
        self._audit = audit
        self._consent = consent

    def evaluate_user(
        self,
        owner_id: str,
        settings: UserSettings,
        now: int,
        window_id: str,
    ) -> list[dict]:
        """Evaluate this user's contacts for the given window; return newly generated reminders."""
        if settings.paused:
            return []  # global pause (FR-7.2) — generate nothing (AC-06)

        existing = self._repo.list(owner_id, "reminder")
        existing_keys = {r.get("idempotency_key") for r in existing}
        window_count = sum(1 for r in existing if r.get("window_id") == window_id)

        categories = {c["id"]: c for c in self._repo.list(owner_id, "category")}
        generated: list[dict] = []

        for contact in self._repo.list(owner_id, "contact"):  # bounded by contact quota (AC-04)
            if window_count >= settings.per_window_cap:
                self._audit.append("scheduler.cap_reached", principal=owner_id,
                                   object_ref=f"window:{window_id}")  # AC-03
                break  # fail closed: no further reminders this window (AC-02)

            key = f"{contact['id']}:{window_id}"
            if key in existing_keys:
                continue  # idempotent: already generated for this window (AC-02)
            if not self._is_due(owner_id, contact, categories, settings, now):
                continue  # one of the four conditions false -> no reminder (AC-03/AC-05)

            reminder = self._repo.add(owner_id, "reminder", key.replace(":", "-"), {
                "contact_id": contact["id"],
                "channel": settings.channel,
                "status": "pending",
                "due_at": now,
                "idempotency_key": key,
                "window_id": window_id,
            })
            generated.append(reminder)
            existing_keys.add(key)
            window_count += 1
        return generated

    def _is_due(self, owner_id, contact, categories, settings: UserSettings, now: int) -> bool:
        # 1. snooze
        snooze_until = contact.get("snooze_until")
        if snooze_until is not None and snooze_until > now:
            return False
        # 2. cadence elapsed
        category = categories.get(contact.get("category_id"))
        if category is None:
            return False  # no category -> cannot resolve cadence; fail closed
        cadence_days = effective_cadence_days(contact, category)
        last = contact.get("last_contacted_at")
        if last is not None and (now - last) < cadence_days * _DAY_SECONDS:
            return False
        # 3. send window (unknown timezone fails closed, AC-05)
        if not is_delivery_allowed(now, settings.timezone, settings.quiet_hours):
            return False
        # 4. channel consent present (indeterminate/absent fails closed, AC-05)
        if not is_delivery_consented(self._consent, owner_id, settings.channel, now, self._audit):
            return False
        return True
