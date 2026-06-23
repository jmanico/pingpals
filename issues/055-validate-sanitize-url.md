# Requirement: `validateAndSanitizeUrl` utility + exhaustive scheme/host tests

## Metadata
- **ID**: REQ-FE-055
- **Title**: Allowlist URL validator/sanitizer for all hrefs, srcs, and outreach deep links
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Critical
- **Classification**: Security

## Requirement
- **Description**: The frontend MUST provide a single pure function `validateAndSanitizeUrl(raw: string): string` that returns the input URL only if it passes an allowlist scheme/host check, and otherwise returns the safe fallback `"#"`. Every `href` and `src` in the application — and every outreach deep link — MUST be passed through this function before it reaches the DOM. Allowed schemes: `mailto`, `tel`, `sms`, `https` (restricted to the preregistered click-to-chat host allowlist, e.g. `wa.me`), and the Signal scheme. The `https` host MUST be matched by **exact string comparison** (no suffix/substring/wildcard). Any contact-derived component (phone, handle) MUST be schema-validated and percent-encoded before insertion and MUST NOT be able to alter the scheme, host, or authority; if it would, the URL MUST be rejected to `"#"`.
- **Rationale**: Prevents `javascript:`/`data:` and lookalike-host injection from reaching a link sink (XSS / open-redirect / spoofed outreach). This is the single client-side chokepoint behind `FR-6.4`, `FE-1.3`, and ARCHITECTURE Dependency Rule 6 ("No URL reaches a sink without passing the scheme allowlist; failure resolves to `#`").
- **Design**: Per `DESIGN.md` §7, a reminder card renders exactly one outreach action; an invalid URL renders as a disabled/`#` affordance rather than a live link. The function is presentation-agnostic and consumed by every link component.

## Scope
- **Applies To**: Web App
- **Components**: React 19 SPA — shared `lib/url` utility; consumed by reminder card, contact views, any anchor/image component.
- **Actors**: Authenticated user (owner) rendering their own data; contact-derived strings are untrusted input.
- **Data Classification**: Restricted (contact phone/handle are personal data); the function itself stores nothing.

## Security Context
- **Defense Layer**: Input Validation + Output Encoding (allowlist + percent-encoding)
- **Threat(s) Addressed**: XSS via `javascript:`/`data:` URIs (CWE-79, OWASP A03:2021), open redirect / host spoofing (CWE-601), URL authority confusion. STRIDE: Tampering, Spoofing.
- **Trust Boundary**: Client-side render boundary — the last gate before a string becomes a live DOM `href`/`src`. (Server-side outreach-link construction is the sibling control in issue 043; this is the independent client gate — defense in depth, neither trusts the other.)
- **Zero Trust Consideration**: Treats every URL — including ones returned by the API — as untrusted and re-validates at render time; the client makes no trust assumption from the data's origin.

## Standards Alignment
- **OWASP ASVS**: V5.1 (input validation), V5.3 (output encoding / injection prevention)
- **OWASP AISVS**: n/a (no AI component)
- **NIST SP 800-53**: SI-10 (information input validation)
- **NIST SP 800-207**: untrusted-input handling inside the boundary
- **Regulatory**: n/a
- **Other**: WHATWG URL standard; `FR-6.4`, `FE-1.3`, `SEC-4.3`, ARCH Dependency Rule 6

## Acceptance Criteria
1. **AC-01**: Given a `mailto:`, `tel:`, `sms:`, or Signal-scheme URL with a validated, percent-encoded contact component, when sanitized, then the function returns the URL unchanged.
2. **AC-02**: Given `https://wa.me/<digits>` where the host equals an allowlisted click-to-chat host by exact string comparison, when sanitized, then the URL is returned; given `https://wa.me.evil.example/...`, then the function returns `"#"`. *(verbatim `FR-6.4`: a lookalike-host URL is rejected to `"#"`.)*
3. **AC-03 (negative)**: Given a `javascript:`, `data:`, `file:`, or any non-allowlisted scheme URL, when sanitized, then the function returns `"#"` and the value never reaches a DOM `href`/`src`. *(verbatim `FR-6.4`: a `javascript:` or `data:` scheme URL never reaches the DOM as an href.)*
4. **AC-04 (negative)**: Given a contact-derived component crafted to inject an authority (e.g. `tel:` value containing `//evil.example`), when building the URL, then the component cannot alter scheme/host/authority and the result is rejected to `"#"` rather than coerced.

## Failure Behavior
- **On Invalid Input**: Return `"#"` (safe fallback). Never throw into render; never partially sanitize. Optionally emit a client telemetry counter (no URL contents, no PII).
- **On System Error**: Fail closed — any internal error returns `"#"`.
- **Alerting**: A spike in fallback rate MAY raise a frontend-health alert; not security-blocking.

## Test Strategy
- **Unit Tests**: Exhaustive table-driven cases per scheme (allowed + rejected), exact-host match vs. suffix/substring/wildcard lookalikes, percent-encoding of contact components, authority-injection attempts, empty/`null`/whitespace, mixed-case schemes, embedded control chars.
- **Integration Tests**: Render a reminder card and a contact view; assert the produced `href` is either an allowlisted URL or exactly `"#"`.
- **Security Tests**: Fuzz with a `javascript:`/`data:`/lookalike-host corpus; assert no input yields a live disallowed href (maps to TEST-1.3 "outreach URL scheme rejection").
- **Compliance Tests**: n/a
- **Coverage Target**: ≥ 80% branch coverage of the module (aim 100% — it is small and security-critical).

## Dependencies
- **Upstream**: 054 (React SPA scaffold), 005 (design tokens for the disabled-link affordance).
- **Downstream**: 061 (reminder card UI), 059 (contact UI), 043 (server outreach-link service — mirror allowlist), 066 (security test suite consumes these cases).
- **External**: None (use the platform `URL` API; do not add a URL-parsing dependency without `SEC-9.x` vetting).

## Implementation Notes
- **Constraints**: Pure, synchronous, dependency-free; no network. Host allowlist is a hard-coded constant array compared by `===`. Length-cap the input before parsing (ReDoS/abuse).
- **Anti-Patterns**: MUST NOT use substring/regex host matching; MUST NOT rely on `dangerouslySetInnerHTML` anywhere (`FE-1.1`); MUST NOT "fix" a bad URL by stripping the scheme — reject to `"#"`; MUST NOT trust API-provided URLs without re-validation.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** This is a small but security-critical chokepoint where a subtle allowlist/encoding mistake is a directly exploitable vulnerability; favor the model with the strongest adversarial-reasoning on URL-parsing edge cases. Mandatory human security review before merge. Mirror the allowlist with the server-side validator (issue 043) and keep them in sync.
