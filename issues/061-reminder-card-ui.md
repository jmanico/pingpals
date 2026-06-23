# Requirement: Reminder card UI (minimal payload, single outreach action, snooze/dismiss/mark-contacted)

## Metadata
- **ID**: REQ-FE-061
- **Title**: Reminder list + speech-bubble reminder card with minimal payload and one outreach action
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Functional

## Requirement
- **Description**: The frontend MUST render the user's due reminders as a list of cards. Each reminder card MUST display only the minimal payload — the contact display name, the chosen channel, and exactly one one-tap outreach action — and MUST NOT show tokens, secrets, or unnecessary personal data. The single outreach action MUST be rendered through `validateAndSanitizeUrl` (055), producing `"#"` (a disabled affordance) if invalid. Each card MUST offer snooze, dismiss, and mark-as-contacted actions (issue 033); mark-as-contacted resets the cadence clock server-side. The card MUST NOT transmit any message into a third-party platform itself — it only opens the user's own app via the deep link.
- **Rationale**: This is the user-facing surface of `FR-5.1`–`FR-5.4` and `FR-6.3`–`FR-6.4`. `FR-5.4`'s minimal-payload rule and the outreach-deep-link-only boundary (REQUIREMENTS §1) are core privacy/security invariants; the card must embody them. Where a reminder arrived via an opaque-id channel (`FR-5.6`), the card fetches the displayable detail only after an authenticated in-app fetch.
- **Design**: Per `DESIGN.md` §5 and §7, the card uses the purple speech-bubble motif (the "…" pending-ping bubble) on a white card surface, showing the contact display name, the channel, and a single Royal Purple one-tap action. Reminder copy uses DESIGN §6 voice ("Your Majesty, it's been a while since you pinged Alex. Send word?"); a successful mark-contacted shows the celebratory "Long live the streak! 👑" moment (DESIGN §5 mascot, §6). Status (due soon / overdue) uses semantic tokens (`--color-warning`/`--color-danger`) paired with an icon+label, never color alone (DESIGN §3.3, §3.4).

## Scope
- **Applies To**: Web App
- **Components**: React 19 SPA — reminder list, reminder card, snooze/dismiss/mark-contacted controls; consumes API client (057), URL validator (055), Zod (056), component library (064).
- **Actors**: Authenticated user (owner) acting on their own reminders.
- **Data Classification**: Restricted (contact display name, channel); the card deliberately excludes tokens and unnecessary personal data (`FR-5.4`).

## Security Context
- **Defense Layer**: Output Encoding / data minimization (minimal payload) + Output Validation (safe outreach URL).
- **Threat(s) Addressed**: Over-exposure of personal data / secrets in the reminder surface (CWE-200, mitigated by minimal payload), malicious outreach URL reaching the DOM (`javascript:`/lookalike, CWE-79/CWE-601, addressed by 055), unintended message transmission into third-party platforms (out-of-scope boundary, REQUIREMENTS §1/§2.3). STRIDE: Information Disclosure, Tampering.
- **Trust Boundary**: Client render boundary. The card renders only the minimal API-supplied payload for the owning user and re-validates the outreach URL at render (055); it makes no authorization decision (ARCH Rule 1) and never sends into a third-party platform.
- **Zero Trust Consideration**: Even the API-supplied outreach link is treated as untrusted and re-sanitized at render; contact-derived components never alter the URL authority (055). The card assumes nothing beyond what the minimal payload contains.

## Standards Alignment
- **OWASP ASVS**: V5.3 (output encoding), V8.1 (data minimization in client)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SC-28-adjacent data minimization, SI-10 (input validation of URLs)
- **NIST SP 800-207**: render-time re-validation of untrusted data
- **Regulatory**: GDPR Art. 5 (data minimization, purpose limitation)
- **Other**: `FR-5.1`, `FR-5.3`, `FR-5.4`, `FR-6.3`, `FR-6.4`, `FE-1.3`, `PRIV-1.8`

## Acceptance Criteria
1. **AC-01**: Given a due reminder, when its card renders, then it shows only the contact display name, the chosen channel, and exactly one one-tap outreach action. *(verbatim `FR-5.4`: the reminder payload MUST contain only the data needed to act … MUST NOT embed tokens, secrets, or unnecessary personal data.)*
2. **AC-02 (negative)**: Given a reminder payload, when rendered, then no token, secret, or unnecessary personal data appears anywhere on the card.
3. **AC-03**: Given the card's outreach action, when rendered, then its href passes `validateAndSanitizeUrl` (055); an invalid URL renders as `"#"` (disabled affordance) and never reaches the DOM as a live link. *(verbatim `FR-6.4`: a `javascript:`/`data:` URL never reaches the DOM as an href.)*
4. **AC-04**: Given the card actions, when the user snoozes, dismisses, or marks-as-contacted, then the corresponding server action (033) is invoked; mark-as-contacted reflects the reset cadence clock and shows the celebratory success state. *(verbatim `FR-5.3`: the user MUST be able to snooze, dismiss, or mark a reminder as contacted.)*
5. **AC-05 (negative)**: Given the card, when the outreach action is triggered, then it only opens the user's own app via the deep link and the system transmits no message into any third-party platform (`FR-6.3`).
6. **AC-06 (accessibility)**: Given a reminder card, when rendered, then status (due soon/overdue) is conveyed by icon+label not color alone, actions are keyboard-operable with a visible Gilt focus ring, and contrast meets WCAG 2.2 AA (`NFR-1.4`, DESIGN §3.4).

## Failure Behavior
- **On Invalid Input**: An invalid outreach URL renders `"#"` (disabled) rather than a live link; an invalid reminder payload (failing 056) is not rendered (fail closed).
- **On System Error**: Fail closed — a failed snooze/dismiss/mark action shows a gentle error and does not optimistically clear the reminder; the cadence clock is reset only when the server confirms.
- **Alerting**: n/a at UI layer; delivery/action audit is server-side (`SEC-8.1`, issue 042).

## Test Strategy
- **Unit Tests**: Card renders exactly one outreach action and the minimal field set; no token/secret field rendered; outreach href routed through 055 (valid → URL, invalid → `"#"`); action buttons invoke snooze/dismiss/mark.
- **Integration Tests**: Reminder list fetch (031/033) renders cards; mark-as-contacted resets the clock server-side and shows success; opaque-id channel reminders fetch detail in-app before showing the name (`FR-5.6`).
- **Security Tests**: Inject a `javascript:`/lookalike outreach URL and assert `"#"` (maps to FR-6.4/055); assert no secret/token leaks into the card DOM (maps to FR-5.4).
- **Compliance Tests**: Confirm payload-minimization (no extra personal data) for representative reminders.
- **Coverage Target**: ≥ 80% branch coverage of reminder list/card components and action logic.

## Dependencies
- **Upstream**: 054 (scaffold), 055 (URL validator), 056 (Zod), 057 (API client), 064 (component library), 005 (tokens), 031 (scheduler/reminder source), 033 (snooze/dismiss/mark actions), 043 (server outreach-link service supplying the deep link).
- **Downstream**: 062 (notification preferences influence channel shown), 044 (preferences affect which channel a reminder uses).
- **External**: The user's own messaging apps (opened via deep link); the card never integrates a third-party send API.

## Implementation Notes
- **Constraints**: Minimal payload only — display name, channel, one action (`FR-5.4`). Exactly one outreach action per card; rendered via 055. Never transmit into a third-party platform (REQUIREMENTS §1, §2.3). For opaque-id channels, fetch displayable detail only after an authenticated in-app call (`FR-5.6`). All styling via tokens (005).
- **Anti-Patterns**: MUST NOT show tokens/secrets/unnecessary personal data on the card (`FR-5.4`); MUST NOT render an unsanitized outreach href (`FE-1.3`/055); MUST NOT transmit a message into wa.me/SMS/Signal/etc. itself (`FR-6.3`); MUST NOT use array index keys for the reminder list (`FE-1.6`); MUST NOT optimistically clear a reminder before server confirmation; MUST NOT hard-code styling (DESIGN §7.1).
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** The card is a well-specified, brand-driven UI component; breadth and adherence to a fixed minimal-payload + design-token contract dominate. Human review must confirm the minimal-payload rule, the single-action constraint, and that every outreach link routes through issue 055.
