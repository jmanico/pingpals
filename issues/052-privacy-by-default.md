# Requirement: Privacy-by-default settings and restricted free-text notes handling

## Metadata
- **ID**: REQ-PRIV-052
- **Title**: Most-privacy-protective defaults and display-only restricted handling of free-text notes
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Medium
- **Classification**: Privacy

## Requirement
- **Description**: The system MUST apply privacy by design and by default (Article 25): defaults MUST be the most privacy-protective available — integrations off, automatic last-contact detection off, minimum scopes (`PRIV-1.13`). Free-text fields holding contact personal data (notably the contact notes field) are treated as Restricted and inherit all minimization, retention, export, and erasure controls of structured contact data (`PRIV-1.7`, `PRIV-1.8`, `PRIV-1.18`). Because such fields can capture GDPR Article 9 special-category data for which no lawful-processing condition is established, the system MUST advise the user at the point of entry that special-category data SHOULD NOT be entered, and MUST NOT derive, index, or further process the contents of free-text notes for any purpose beyond display to the owning user; absent an established Article 9 condition the system fails closed to display-only. The DPIA (issue 053) and Legitimate Interests Assessment MUST record this residual risk and the chosen mitigation.
- **Rationale**: GDPR Article 25 mandates privacy-protective defaults; Article 9 prohibits processing special-category data without a specific condition, none of which Pingpals establishes (`PRIV-1.1` covers only Art. 6(1)(f)). A free-text notes field is the most likely place special-category data leaks in, so it is constrained to display-only and flagged at entry. This is the data-of-record behind `PRIV-1.13` and `PRIV-1.18`.
- **Design**: Per `DESIGN.md` §6/§7, the point-of-entry advisory uses the gentle royal voice (a light, non-alarming note near the notes field); default-off toggles for integrations/detection are presented as clearly off in the privacy settings.

## Scope
- **Applies To**: Both
- **Components**: Privacy/DSR subsystem (default settings) + contact model/notes field (024) + integration adapters (default off) + web client (entry-point advisory, default-off toggles).
- **Actors**: Authenticated user (owner) — the only party who may see notes content; no service component may process it beyond owner display.
- **Data Classification**: Restricted/PII (notes are contact personal data; may inadvertently include Article 9 special-category data).

## Security Context
- **Defense Layer**: Architecture (default-deny settings + purpose-limited handling) + Sanitization-free display (encode, don't transform)
- **Threat(s) Addressed**: Over-collection / function creep (privacy harm), inadvertent special-category processing without a lawful condition, integration/detection enabled by default leaking data. STRIDE: Information Disclosure.
- **Trust Boundary**: API service — notes content never crosses into any processing pipeline (search index, analytics, LLM, detection) beyond returning it to the owning user for display.
- **Zero Trust Consideration**: Notes content is treated as untrusted-for-processing: the system assumes it may contain special-category data and therefore refuses to derive, index, or further process it — failing closed to display-only.

## Standards Alignment
- **OWASP ASVS**: V8.x (data protection / minimization), V5.3 (output encoding for display)
- **OWASP AISVS**: n/a now; if notes ever feed an LLM, REQUIREMENTS §12 controls apply (display-only forbids this today)
- **NIST SP 800-53**: AC-6 (least privilege), SI-12 (handling), PL-8 / privacy controls (minimization, purpose limitation)
- **NIST SP 800-207**: least-privilege default state
- **Regulatory**: GDPR Arts. 25 (by design/default), 9 (special categories), 5(1)(b) (purpose limitation), 5(1)(c) (minimization)
- **Other**: `PRIV-1.13`, `PRIV-1.18`, `PRIV-1.7`, `PRIV-1.8`, `PRIV-1.1`

## Acceptance Criteria
1. **AC-01**: Given a new account/contact, when defaults are inspected, then integrations are off, automatic last-contact detection is off, and every requested provider scope is the minimum for its function (`PRIV-1.13`).
2. **AC-02 (verbatim `PRIV-1.18`)**: Given a privacy review, when conducted, then the point-of-entry notice is present, notes content is never used as a processing input beyond owner display, and the DPIA records the Article 9 residual-risk decision.
3. **AC-03**: Given notes content, when rendered, then it is contextually encoded for display only and inherits the minimization, retention (051), export (046), and erasure (048) controls of structured contact data.
4. **AC-04 (negative)**: Given any feature attempts to derive, index, search, or further process notes content, when invoked, then the operation is refused (display-only fail-closed) absent an established Article 9 condition.
5. **AC-05 (negative)**: Given a user has not affirmatively enabled an integration or detection, when the scheduler/adapters run, then no integration or detection processing occurs (default off).

## Failure Behavior
- **On Invalid Input**: Notes exceeding bounds are rejected with a field-level error (reject over sanitize, `FR-1.4`); the entry advisory does not block valid input.
- **On System Error**: Fail closed — if it cannot be confirmed that a setting is the privacy-protective default, treat it as off/minimum; if notes-processing constraints cannot be enforced, refuse the processing.
- **Alerting**: A code path that attempts to process notes beyond display is a defect; flag in review/SAST rather than runtime alert.

## Test Strategy
- **Unit Tests**: Default-state assertions (integrations/detection off, minimum scopes); notes bounds; encode-on-display.
- **Integration Tests**: New account exposes only privacy-protective defaults; enabling an integration requires explicit user action + recorded consent (045); notes round-trip through export (046) and erasure (048).
- **Security Tests**: Assert no pipeline (index/analytics/detection/LLM) consumes notes content; SAST rule flags any notes-derivation path.
- **Compliance Tests**: Automated evidence the entry-point advisory is rendered and that the DPIA (053) records the Article 9 residual-risk decision.
- **Coverage Target**: ≥ 80% branch coverage of the defaults + notes-handling logic.

## Dependencies
- **Upstream**: 024 (contact model incl. notes field), 022 (integration adapters — default off, minimum scope), 045 (consent gates any opt-in), 009 (input validation/bounds for notes), 005 (design tokens for the advisory).
- **Downstream**: 046 (notes in export), 048 (notes in erasure), 051 (notes retention), 053 (DPIA/LIA record the Art. 9 residual risk).
- **External**: Provider scopes (Google People — minimum contacts-read) governed by 022; KMS via 011 for notes at rest.

## Implementation Notes
- **Constraints**: All integration/detection settings default off and require an explicit, consented opt-in (045). Notes are encoded-for-display only and never enter a processing pipeline. Article 9 residual-risk decision is recorded in 053 (DPIA/LIA) — flag as a human gate, not auto-resolvable.
- **Anti-Patterns**: MUST NOT default any integration or detection on; MUST NOT request broader-than-minimum scopes; MUST NOT index/search/analyze/feed-to-LLM notes content; MUST NOT sanitize/transform notes instead of rejecting over-bounds input.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Broad settings-default and field-handling work that is well-bounded once the default matrix and the display-only constraint are enumerated. Mandatory human privacy review of the entry-point advisory copy and confirmation that no pipeline consumes notes; the Article 9 residual-risk decision is a human gate recorded in issue 053.
