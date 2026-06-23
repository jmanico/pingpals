# Requirement: Accessible component library on design tokens (WCAG 2.2 AA)

## Metadata
- **ID**: REQ-FE-064
- **Title**: Token-driven base component library meeting WCAG 2.2 AA (buttons, cards, forms, inputs, focus ring)
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Functional

## Requirement
- **Description**: The frontend MUST provide a base component library — at minimum buttons, cards, forms, inputs, and a shared focus ring — built exclusively on design tokens (issue 005) with no hard-coded visual values. Every text/background and UI pairing MUST meet WCAG 2.2 AA contrast: 4.5:1 for body text and 3:1 for large text and non-text UI components. A visible focus indicator (the Gilt `#F4C95D` focus ring) MUST be present on every interactive element and MUST NOT be removed. Color MUST NOT be the sole means of conveying status; status MUST be paired with an icon and/or text label. Components MUST follow the scaffold's secure invariants (no `dangerouslySetInnerHTML`, no prop-spread onto DOM nodes, `crypto.randomUUID` keys, Zod-validated data).
- **Rationale**: A single accessible, token-driven primitive set makes WCAG 2.2 AA (`NFR-1.4`) and the DESIGN §3.4 normative accessibility MUSTs the default for every screen (058–063) rather than a per-screen retrofit, and centralizes theming/rebranding (DESIGN §7.1). It encodes the brand (DESIGN §7) once.
- **Design**: Per `DESIGN.md` §7 and §7.1, primitives consume the token file (palette, type scale, spacing, radii) — never literals. The primary button is Royal Purple (`--color-purple-700`) with an Ermine White label, hover to Amethyst; gold is reserved as an accent (trim, not upholstery — DESIGN §3.2) for a single hero CTA per view. Surfaces are white cards with soft shadows and gently rounded corners on a Parchment background (DESIGN §7). The focus ring is Gilt and always visible (DESIGN §7). Crown/speech-bubble motifs (DESIGN §5) and the King Ping mascot are available as shared brand components. Body text defaults to Plum Ink on Parchment (the AA-compliant pairing); gold is never used for body copy on light backgrounds (DESIGN §3.4).

## Scope
- **Applies To**: Web App
- **Components**: React 19 SPA — shared component library (buttons, cards, form fields, inputs, focus-ring utility, status/badge, mascot/crown/speech-bubble brand marks); consumed by all feature UIs (058–063).
- **Actors**: Authenticated user (owner) — including users relying on assistive technology, keyboard navigation, and high-contrast needs.
- **Data Classification**: Internal (the primitives carry no personal data; they render data supplied by feature modules).

## Security Context
- **Defense Layer**: Architecture (secure, accessible, token-driven primitives) + Output Encoding posture inherited from the scaffold.
- **Threat(s) Addressed**: Inaccessible UI excluding users (compliance/usability risk, `NFR-1.4`), status conveyed by color alone failing color-vision-deficient users, removed focus indicators harming keyboard users; carries forward XSS/prop-injection avoidance from the scaffold (CWE-79, CWE-915). STRIDE: n/a primarily (accessibility/quality), Tampering avoidance inherited.
- **Trust Boundary**: Client render boundary. Primitives render only validated data passed by feature modules (056) and apply the scaffold's safe-render invariants (054); they make no authorization decision.
- **Zero Trust Consideration**: Components assume any string/URL they receive may be untrusted — text is escaped by default (no raw HTML), and any href/src they expose routes through `validateAndSanitizeUrl` (055).

## Standards Alignment
- **OWASP ASVS**: V5.3 (output encoding), V14 (configuration / CSP-compatible rendering)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SI-10 (input validation — inherited), AC-3 (no client authz)
- **NIST SP 800-207**: client presents only; no trust decision
- **Regulatory**: n/a directly (accessibility obligation via `NFR-1.4`)
- **Other**: WCAG 2.2 AA, WAI-ARIA; `NFR-1.4`, `FE-1.1`, `FE-1.5`, `FE-1.6`, DESIGN §3.4, §7, §7.1

## Acceptance Criteria
1. **AC-01**: Given any component, when inspected, then all visual values resolve from design tokens (005) with no hard-coded hex/px literals (DESIGN §7.1).
2. **AC-02**: Given any text/background or UI pairing, when measured, then it meets WCAG 2.2 AA contrast — 4.5:1 for body, 3:1 for large text / UI. *(verbatim DESIGN §3.4: all text/background pairings MUST meet WCAG 2.2 AA contrast, per `NFR-1.4`.)*
3. **AC-03 (negative)**: Given Royal Gold (`#E2A52B`) as body text on a light background, when attempted, then it is disallowed (it fails contrast). *(verbatim DESIGN §3.4: never use Royal Gold for body copy on light backgrounds.)*
4. **AC-04 (negative)**: Given status (e.g. overdue), when conveyed, then it is not by color alone — it is paired with an icon and/or label. *(verbatim DESIGN §3.4: color MUST NOT be the sole means of conveying status.)*
5. **AC-05**: Given any interactive element, when focused, then a visible Gilt focus ring is shown and is never removed. *(verbatim DESIGN §7: a Gilt focus ring — never remove focus outlines.)*
6. **AC-06**: Given the secure-render invariants, when components render, then none use `dangerouslySetInnerHTML` (`FE-1.1`), none spread props onto DOM nodes (`FE-1.5`), and list keys use `crypto.randomUUID`/domain ids not array index (`FE-1.6`).
7. **AC-07 (accessibility)**: Given components are operated by keyboard and screen reader, when navigated, then all interactive primitives are reachable/operable by keyboard, have accessible names/roles, and form fields associate labels and error messages (`NFR-1.4`).

## Failure Behavior
- **On Invalid Input**: A component given an invalid href/src renders the safe `"#"` fallback (via 055); a field error renders accessibly (associated, text+icon).
- **On System Error**: Fail closed on rendering safety — never fall back to raw HTML or an unsanitized URL; an automated contrast/a11y check failure blocks the build (CI gate).
- **Alerting**: Accessibility/contrast regressions are CI-blocking; no runtime alert.

## Test Strategy
- **Unit Tests**: Each primitive renders from tokens (no literals); contrast assertions for token pairings; focus ring present and not removable; status components require an icon/label alongside color; key generation uses UUID/domain id.
- **Integration Tests**: Compose representative screens (reminder card 061, contact form 059) from primitives and run automated accessibility checks (axe-style) for AA contrast, focus visibility, and labeling.
- **Security Tests**: Confirm no `dangerouslySetInnerHTML`/prop-spread/array-index keys in any primitive (lint gate from 054); confirm href/src primitives route through 055.
- **Compliance Tests**: CI evidence that the WCAG 2.2 AA gate (`NFR-1.4`) and DESIGN §3.4 MUSTs are enforced and blocking.
- **Coverage Target**: ≥ 80% branch coverage of the component library.

## Dependencies
- **Upstream**: 054 (SPA scaffold + secure-render invariants), 005 (design tokens), 055 (URL validator for href/src primitives), 056 (Zod for any data-bound primitive), 003 (CI to enforce the a11y/contrast gate).
- **Downstream**: 058, 059, 060, 061, 062, 063 (all feature UIs are composed from this library).
- **External**: An accessibility test runner (e.g. axe-core) — vetted per `SEC-9.1`; no UI framework that injects raw HTML or requires `unsafe-inline`.

## Implementation Notes
- **Constraints**: Tokens only — no hard-coded values anywhere (DESIGN §7.1). WCAG 2.2 AA is a CI-blocking gate (`NFR-1.4`). The Gilt focus ring is always visible. Default body pairing is Plum Ink on Parchment (DESIGN §3.4); gold is accent-only. Inherit the scaffold's secure-render invariants (054).
- **Anti-Patterns**: MUST NOT hard-code hex/px (DESIGN §7.1); MUST NOT use gold for body text on light backgrounds (DESIGN §3.4); MUST NOT convey status by color alone (DESIGN §3.4); MUST NOT remove focus outlines (DESIGN §7); MUST NOT use `dangerouslySetInnerHTML` (`FE-1.1`) or spread props onto DOM nodes (`FE-1.5`); MUST NOT use array index keys (`FE-1.6`).
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** A design-system primitive library is broad, repetitive, token-and-pattern-driven work where consistency across many components is the main demand. Human review must confirm automated WCAG 2.2 AA contrast/focus/label gates actually block regressions, and that the DESIGN §3.4 normative MUSTs are enforced.
