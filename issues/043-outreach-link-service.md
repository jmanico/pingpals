# Requirement: Server-side outreach deep-link builder behind an allowlist validator

## Metadata
- **ID**: REQ-DEL-043
- **Title**: Allowlist-validated outreach deep-link construction (mirror of the client validator)
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Critical
- **Classification**: Security

## Requirement
- **Description**: The system MUST provide a server-side outreach deep-link builder that constructs every outreach action behind an **allowlist validator** before the link is returned to the client or placed in any reminder payload. Allowed schemes: `mailto`, `tel`, `sms`, `https` (restricted to a **preregistered click-to-chat host allowlist**, e.g. `wa.me`, matched by **exact string comparison** — no suffix, substring, or wildcard), and the Signal scheme. Any contact-derived component (phone, handle) MUST be schema-validated and **percent-encoded** before insertion and MUST NOT be able to alter the scheme, host, or authority of the resulting URL; if it would, the URL MUST be **rejected**. Any other scheme or non-allowlisted host MUST be rejected and replaced with the safe fallback `"#"`. The system MUST NOT transmit any message into these platforms itself — it only produces a link the user opens in their own app.
- **Rationale**: An outreach link embeds untrusted contact-derived data and is opened by the user; a `javascript:`/`data:` scheme or a lookalike host (`wa.me.evil.example`) is an XSS/open-redirect/spoofed-outreach vector (`FR-6.4`, `SEC-4.3`). Building and validating links server-side keeps the authority for link construction inside the trust boundary; this is the **server mirror** of the client validator in issue 055 — defense in depth, neither side trusting the other.
- **Design**: Per `DESIGN.md` §7, the reminder card renders exactly one outreach action; a rejected link surfaces as a disabled/`"#"` affordance, never a live broken link. The non-transmission boundary (`REQUIREMENTS.md` §1) is preserved: Pingpals hands over a link, never a sent message.

## Scope
- **Applies To**: API / Backend (outreach-link service)
- **Components**: Outreach-link builder + allowlist validator (server); shared validation framework (009); reminder payload builder (036); consumed by delivery adapters (038/040) and reminder API responses; mirrors client validator (055).
- **Actors**: Authenticated user (owner, opens the link). Contact-derived phone/handle are untrusted input.
- **Data Classification**: Restricted (contact phone/handle); the service stores nothing.

## Security Context
- **Defense Layer**: Input Validation + Output Encoding (allowlist + percent-encoding)
- **Threat(s) Addressed**: XSS via `javascript:`/`data:` URIs (CWE-79, OWASP A03:2021), open redirect / host spoofing (CWE-601), URL authority confusion (CWE-99). STRIDE: Tampering, Spoofing.
- **Trust Boundary**: Server-side link-construction boundary — the last server gate before an outreach URL is returned to the client or embedded in a payload. The client re-validates independently (issue 055).
- **Zero Trust Consideration**: Treats every contact-derived component as untrusted; validates against an explicit schema, percent-encodes, and rejects anything that could alter scheme/host/authority — assuming nothing from the data's stored origin.

## Standards Alignment
- **OWASP ASVS**: V5.1 (input validation), V5.3 (output encoding / injection prevention)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SI-10 (input validation), SC-8 (output integrity)
- **NIST SP 800-207**: untrusted-input handling inside the boundary
- **Regulatory**: n/a (security control; supports the non-transmission boundary of §1)
- **Other**: `FR-6.3`, `FR-6.4`, `SEC-4.3`, ARCH Dependency Rule 6; mirrors `FE-1.3` (issue 055)

## Acceptance Criteria
1. **AC-01**: Given a `mailto:`/`tel:`/`sms:`/Signal-scheme outreach action with a schema-validated, percent-encoded contact component, when built, then the validator returns the URL unchanged.
2. **AC-02 (verbatim `FR-6.4`)**: Given an `https://wa.me/<digits>` whose host equals an allowlisted click-to-chat host by exact string comparison, then it is returned; given `https://wa.me.evil.example/...`, then the lookalike-host URL is rejected to `"#"`.
3. **AC-03 (negative, verbatim `FR-6.4`)**: Given a `javascript:` or `data:` scheme URL, when processed, then it never reaches the client/payload as a live href and resolves to `"#"`.
4. **AC-04 (negative)**: Given a contact-derived component crafted to inject an authority (e.g. a `tel:`/handle value containing `//evil.example`), when building the URL, then the component cannot alter scheme/host/authority and the result is rejected to `"#"` rather than coerced.
5. **AC-05 (negative)**: Given any outreach action, when built, then the system performs no transmission into the target platform — it only emits a link (§1 boundary).

## Failure Behavior
- **On Invalid Input**: Reject to `"#"` (safe fallback); no partial/"fixed" URL; never throw into the response path; a field-level rejection on the contact-derived component (reject over sanitize, `FR-1.4`).
- **On System Error**: Fail closed — any internal error yields `"#"`.
- **Alerting**: A spike in rejected outreach links MAY indicate malformed/attacker-shaped contact data and SHOULD raise an operational signal (no URL contents/PII in the signal).

## Test Strategy
- **Unit Tests**: Table-driven per scheme (allowed + rejected); exact-host match vs. suffix/substring/wildcard lookalikes; percent-encoding of contact components; authority-injection attempts; empty/null/whitespace; mixed-case schemes; embedded control chars. ReDoS-safe, length-capped before parsing.
- **Integration Tests**: Outreach link returned in a reminder API response / payload is either allowlisted or exactly `"#"`; matches the client validator's verdict on shared cases (parity with issue 055).
- **Security Tests**: Fuzz with a `javascript:`/`data:`/lookalike-host corpus; assert no input yields a live disallowed link (maps to TEST-1.3 "outreach URL scheme rejection").
- **Compliance Tests**: n/a
- **Coverage Target**: ≥ 80% branch coverage (aim 100% — small, security-critical).

## Dependencies
- **Upstream**: 009 (validation framework), 024 (contact schema — phone/handle validators).
- **Downstream**: 036 (payload builder embeds validated links), 038/040 (delivery adapters), reminder API; 055 (client mirror — keep allowlists in sync), 066 (security test suite).
- **External**: None (use the platform URL primitives; no URL-parsing dependency without `SEC-9.x` vetting).

## Implementation Notes
- **Constraints**: Pure/deterministic; host allowlist is a hard-coded constant compared by exact equality; length-cap input before parsing (ReDoS/abuse, SECURITY §4). The allowlist and encoding rules MUST be kept **in lockstep with the client validator (issue 055)**.
- **Anti-Patterns**: MUST NOT use substring/regex/wildcard host matching; MUST NOT "fix" a bad URL by stripping the scheme — reject to `"#"`; MUST NOT let a contact-derived component alter scheme/host/authority; MUST NOT transmit into the target platform; MUST NOT rely on the client validator alone.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** A security-critical chokepoint where a subtle allowlist/encoding mistake is directly exploitable; favor strong adversarial reasoning on URL-parsing edge cases. Mandatory human security review; mirror and keep in sync with issue 055.
