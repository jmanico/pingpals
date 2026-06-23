"""Outreach-link service (stub).

Builds deep links (mailto, tel, sms, https wa.me click-to-chat, Signal) behind an allowlist
scheme+host validator; contact-derived components are schema-validated and percent-encoded and
cannot alter scheme/host/authority. Any disallowed URL resolves to the safe fallback "#". The
system never transmits a message into those platforms itself.
Tags: FR-6.3, FR-6.4, SEC-4.3. Implementation tracked in issue 043.
"""
