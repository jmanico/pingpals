"""Email anti-spoofing policy validation (issue 050, INT-2.3).

The reminder-sending domain MUST publish SPF, DKIM-sign all reminder mail, and publish a DMARC
policy of ``p=reject`` with SPF/DKIM alignment. A reminder-only domain has no legitimate
third-party senders, so ``reject`` is the fail-closed default; ``quarantine`` is allowed ONLY as a
time-boxed rollout step with an explicit (future) expiry, and ``p=none`` (or DKIM disabled) fails
validation. This validates the configured DNS/signing posture (the records are deployment config).
"""

from __future__ import annotations

from dataclasses import dataclass


class EmailAuthError(Exception):
    """The email-authentication posture is non-conformant (fail validation)."""


@dataclass(frozen=True)
class EmailAuthConfig:
    spf_record: str | None
    dkim_selector: str | None
    dkim_public_key: str | None
    dkim_signing_enabled: bool
    dmarc_policy: str            # "reject" | "quarantine" | "none"
    dmarc_aligned: bool
    quarantine_expiry_epoch: int | None = None


def validate_email_auth(config: EmailAuthConfig, now: int) -> None:
    """Raise ``EmailAuthError`` unless the posture conforms to INT-2.3 (AC-01/AC-04/AC-05)."""
    if not config.spf_record:
        raise EmailAuthError("SPF record missing")
    if not (config.dkim_selector and config.dkim_public_key and config.dkim_signing_enabled):
        raise EmailAuthError("DKIM signing must be enabled with a published selector/key")  # AC-05
    if not config.dmarc_aligned:
        raise EmailAuthError("DMARC requires SPF/DKIM alignment")

    policy = config.dmarc_policy.lower()
    if policy == "reject":
        return
    if policy == "quarantine":
        # Allowed only as a time-boxed rollout step with a real future expiry (AC-04).
        if config.quarantine_expiry_epoch is None or config.quarantine_expiry_epoch <= now:
            raise EmailAuthError("quarantine is only a time-boxed step with a future expiry")
        return
    raise EmailAuthError("DMARC policy must be p=reject (p=none is rejected)")  # AC-04
