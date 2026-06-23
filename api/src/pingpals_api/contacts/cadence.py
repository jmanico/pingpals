"""Cadence configuration + quiet-hours/timezone windowing (issue 038, FR-3.1/3.2/3.3).

Cadence is a positive integer day interval with an optional preferred day-of-week and send-time
window. A contact inherits its category default unless a per-contact override is set (the override
wins). Quiet hours + timezone gate delivery; an UNKNOWN timezone FAILS CLOSED to no delivery
(reminders are never delivered outside the allowed window).
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..validation import Field, validate

_CADENCE_SCHEMA = {
    "interval_days": Field("int", required=True, min_value=1, max_value=3650),
    "preferred_dow": Field("int", required=False, min_value=0, max_value=6),
    "send_window_start_min": Field("int", required=False, min_value=0, max_value=1439),
    "send_window_end_min": Field("int", required=False, min_value=0, max_value=1439),
}


def validate_cadence(payload: dict) -> dict:
    """Validate a cadence config; a zero/negative/non-integer interval is rejected (AC-01)."""
    return validate(_CADENCE_SCHEMA, payload)


def effective_cadence_days(contact: dict, category: dict) -> int:
    """Per-contact override wins over the category default (FR-3.2, AC-02)."""
    override = contact.get("cadence_override_days")
    if override is not None:
        return int(override)
    return int(category["default_cadence_days"])


def is_delivery_allowed(
    now_epoch: float,
    tz_name: str | None,
    quiet_hours: tuple[int, int] | None,
) -> bool:
    """True only if ``now`` (in the user's tz) is OUTSIDE quiet hours. Fail closed on unknown tz.

    ``quiet_hours`` is (start_min, end_min) within a day; delivery is blocked inside it. An unknown
    or missing timezone returns False — no delivery (FR-3.3, AC-04).
    """
    if not tz_name:
        return False  # unknown/absent timezone -> fail closed (AC-04)
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return False  # unknown timezone -> fail closed
    local = datetime.fromtimestamp(now_epoch, tz=UTC).astimezone(tz)
    minute_of_day = local.hour * 60 + local.minute
    if quiet_hours is None:
        return True
    start, end = quiet_hours
    if start == end:
        return True  # zero-length quiet window
    if start < end:
        in_quiet = start <= minute_of_day < end
    else:  # window wraps midnight (e.g. 22:00 -> 07:00)
        in_quiet = minute_of_day >= start or minute_of_day < end
    return not in_quiet
