"""Outreach link builder + allowlist validator tests (issue 054 / REQ-DELIVERY-043)."""

from __future__ import annotations

import pytest

from pingpals_api.outreach.links import (
    SAFE_FALLBACK,
    build_mailto,
    build_signal,
    build_sms,
    build_tel,
    build_whatsapp,
    validate_and_sanitize_url,
)


def test_builders_for_valid_components() -> None:
    assert build_mailto("alex@example.com") == "mailto:alex@example.com"  # AC-01
    assert build_tel("+15551234567") == "tel:+15551234567"
    assert build_sms("15551234567") == "sms:+15551234567"
    assert build_whatsapp("+15551234567") == "https://wa.me/15551234567"
    assert build_signal("+15551234567").startswith("signal://")


def test_builders_reject_bad_components_to_fallback() -> None:
    assert build_mailto("not-an-email") == SAFE_FALLBACK
    assert build_tel("12-34-not") == SAFE_FALLBACK
    # AC-04: a phone component trying to inject authority is rejected, not coerced.
    assert build_tel("//evil.example") == SAFE_FALLBACK
    assert build_whatsapp("1//evil") == SAFE_FALLBACK


def test_validate_allows_safe_schemes() -> None:
    for url in ["mailto:a@x.com", "tel:+1555", "sms:+1555", "https://wa.me/1555",
                "signal://send?phone=%2B1555"]:
        assert validate_and_sanitize_url(url) == url  # AC-01/AC-02


def test_validate_rejects_dangerous_schemes() -> None:
    for url in ["javascript:alert(1)", "data:text/html,<script>", "vbscript:x", "file:///etc"]:
        assert validate_and_sanitize_url(url) == SAFE_FALLBACK  # AC-03


def test_validate_exact_host_rejects_lookalike() -> None:
    assert validate_and_sanitize_url("https://wa.me/15551234567") == "https://wa.me/15551234567"
    for bad in ["https://wa.me.evil.example/1555", "https://evil.example/wa.me",
                "https://wa.me@evil.example/", "https://wa.me:8080/x"]:
        assert validate_and_sanitize_url(bad) == SAFE_FALLBACK  # AC-02/AC-04


def test_validate_rejects_authority_injection_on_authorityless_scheme() -> None:
    assert validate_and_sanitize_url("tel://evil.example") == SAFE_FALLBACK  # AC-04
    assert validate_and_sanitize_url("mailto://evil.example") == SAFE_FALLBACK


@pytest.mark.parametrize("bad", ["", None, "   "])
def test_validate_handles_empty(bad) -> None:
    assert validate_and_sanitize_url(bad) == SAFE_FALLBACK
