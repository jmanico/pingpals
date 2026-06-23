"""Outreach deep-link builder + allowlist validator (issue 054, FR-6.3/6.4, SEC-4.3).

The system never transmits into a messaging platform — it only emits a validated deep link for the
user's own app to open. Allowed schemes: ``mailto``, ``tel``, ``sms``, ``https`` (restricted to an
exact-match click-to-chat host), and the Signal scheme. Contact-derived components are
schema-validated and percent-encoded and CANNOT alter the scheme/host/authority; any disallowed
scheme, lookalike host, or authority-injection resolves to the safe fallback ``"#"``.
"""

from __future__ import annotations

from urllib.parse import quote, urlsplit

from ..validation import EMAIL_RE, PHONE_RE

SAFE_FALLBACK = "#"
# Exact-match click-to-chat host allowlist (no suffix/substring/wildcard).
CLICK_TO_CHAT_HOSTS = frozenset({"wa.me"})
ALLOWED_SCHEMES = frozenset({"mailto", "tel", "sms", "https", "signal"})


def _digits(phone: str) -> str | None:
    if PHONE_RE.match(phone) is None:
        return None
    return phone.lstrip("+")


def build_mailto(email: str) -> str:
    if EMAIL_RE.match(email) is None:
        return SAFE_FALLBACK
    return f"mailto:{quote(email, safe='@.')}"


def build_tel(phone: str) -> str:
    digits = _digits(phone)
    return f"tel:+{digits}" if digits else SAFE_FALLBACK


def build_sms(phone: str) -> str:
    digits = _digits(phone)
    return f"sms:+{digits}" if digits else SAFE_FALLBACK


def build_whatsapp(phone: str) -> str:
    """WhatsApp click-to-chat: https://wa.me/<digits> (digits only — no authority injection)."""
    digits = _digits(phone)
    return f"https://wa.me/{digits}" if digits else SAFE_FALLBACK


def build_signal(phone: str) -> str:
    digits = _digits(phone)
    return f"signal://send?phone=%2B{quote(digits)}" if digits else SAFE_FALLBACK


def validate_and_sanitize_url(url: str) -> str:
    """Return ``url`` if it passes the allowlist, else ``"#"`` (the render-time gate, FR-6.4).

    Anything outside the scheme allowlist (e.g. ``javascript:``/``data:``), any non-exact
    click-to-chat host, or any embedded credentials/authority injection resolves to ``"#"``.
    """
    if not url or not isinstance(url, str):
        return SAFE_FALLBACK
    try:
        parts = urlsplit(url)
    except ValueError:
        return SAFE_FALLBACK

    scheme = parts.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        return SAFE_FALLBACK  # javascript:/data:/etc. -> "#" (AC-03)

    if scheme == "https":
        # Exact host match only; reject userinfo/port/lookalikes (AC-02/AC-04).
        if parts.username or parts.password or parts.port:
            return SAFE_FALLBACK
        if parts.hostname not in CLICK_TO_CHAT_HOSTS:
            return SAFE_FALLBACK  # wa.me.evil.example != wa.me
    elif scheme in {"mailto", "tel", "sms"}:
        # These schemes carry no authority; an embedded "//" authority is an injection attempt.
        if url[len(scheme) + 1:].startswith("//"):
            return SAFE_FALLBACK
    return url
