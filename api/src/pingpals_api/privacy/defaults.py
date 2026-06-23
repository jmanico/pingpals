"""Privacy-by-default config + free-text notes Article-9 guard (issue 063, PRIV-1.13/1.18).

Defaults are the most privacy-protective available: all integrations OFF, automatic mailbox
detection OFF, minimum scopes. Free-text notes can capture GDPR Article 9 special-category data for
which no lawful-processing condition is established, so the system advises against entering it at
the point of entry and treats notes as DISPLAY-ONLY — it never derives, indexes, or further
processes them (purpose limitation, PRIV-1.8).
"""

from __future__ import annotations

from dataclasses import dataclass, field

NOTES_ENTRY_NOTICE = (
    "Avoid entering special-category data (health, religion, political, sexual-orientation, or "
    "similar). Notes are shown only to you and are not processed further."
)


@dataclass(frozen=True)
class PrivacyDefaults:
    """Privacy-by-default posture (Article 25). Every toggle defaults to the safest value."""

    contacts_import_enabled: bool = False
    calendar_read_enabled: bool = False
    mailbox_detection_enabled: bool = False   # opt-in, default off (PRIV-1.13)
    minimum_scopes_only: bool = True
    notes_display_only: bool = True           # notes are never a processing input (PRIV-1.18)

    #: Channels are off until the user grants per-channel consent.
    enabled_channels: tuple[str, ...] = field(default_factory=tuple)


def default_privacy_settings() -> PrivacyDefaults:
    return PrivacyDefaults()


def is_most_restrictive(defaults: PrivacyDefaults) -> bool:
    """True iff the posture is the most privacy-protective (used as a config guard/test)."""
    return (
        not defaults.contacts_import_enabled
        and not defaults.calendar_read_enabled
        and not defaults.mailbox_detection_enabled
        and defaults.minimum_scopes_only
        and defaults.notes_display_only
        and defaults.enabled_channels == ()
    )


class NotesProcessingError(Exception):
    """Raised if notes content is used as a processing input (forbidden — display only)."""


def guard_notes_not_processed(purpose: str) -> None:
    """Fail closed if any code path tries to use notes for anything beyond owner display."""
    if purpose != "display":
        raise NotesProcessingError("contact notes are display-only (PRIV-1.18)")
