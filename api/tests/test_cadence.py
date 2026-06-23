"""Cadence config + quiet-hours/timezone tests (issue 038 / REQ-CONTACTS-027)."""

from __future__ import annotations

import calendar
from datetime import UTC, datetime

import pytest

from pingpals_api.contacts.cadence import (
    effective_cadence_days,
    is_delivery_allowed,
    validate_cadence,
)
from pingpals_api.validation import ValidationError


def test_positive_interval_accepted_zero_rejected() -> None:
    assert validate_cadence({"interval_days": 30})["interval_days"] == 30  # AC-01
    for bad in [0, -5]:
        with pytest.raises(ValidationError):
            validate_cadence({"interval_days": bad})


def test_override_takes_precedence_else_category_default() -> None:
    category = {"default_cadence_days": 60}
    assert effective_cadence_days({}, category) == 60  # AC-02
    assert effective_cadence_days({"cadence_override_days": 7}, category) == 7


def _epoch(y, mo, d, h, mi, tz="UTC") -> float:
    dt = datetime(y, mo, d, h, mi, tzinfo=UTC)
    return calendar.timegm(dt.timetuple())


def test_unknown_timezone_fails_closed() -> None:
    assert is_delivery_allowed(_epoch(2026, 6, 23, 12, 0), "Not/AZone", (0, 0)) is False  # AC-04
    assert is_delivery_allowed(_epoch(2026, 6, 23, 12, 0), None, None) is False


def test_quiet_hours_block_delivery_inside_window() -> None:
    # Quiet 22:00-07:00 (wraps midnight). 02:00 UTC -> blocked; 12:00 UTC -> allowed.
    quiet = (22 * 60, 7 * 60)
    assert is_delivery_allowed(_epoch(2026, 6, 23, 2, 0), "UTC", quiet) is False  # AC-03/AC-05
    assert is_delivery_allowed(_epoch(2026, 6, 23, 12, 0), "UTC", quiet) is True


def test_quiet_hours_same_day_window() -> None:
    quiet = (9 * 60, 17 * 60)  # block 09:00-17:00
    assert is_delivery_allowed(_epoch(2026, 6, 23, 10, 0), "UTC", quiet) is False
    assert is_delivery_allowed(_epoch(2026, 6, 23, 20, 0), "UTC", quiet) is True


def test_timezone_applied() -> None:
    # 12:00 UTC is 04:00 in America/Los_Angeles -> inside a 22:00-07:00 quiet window.
    quiet = (22 * 60, 7 * 60)
    assert is_delivery_allowed(_epoch(2026, 6, 23, 12, 0), "America/Los_Angeles", quiet) is False
