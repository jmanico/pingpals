# Requirement: Notification preferences UI (channel order, per-category overrides, pause, consent toggles)

## Metadata
- **ID**: REQ-FE-062
- **Title**: Notification preferences UI — channel order, per-category overrides, global pause, per-channel consent
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Medium
- **Classification**: Functional

## Requirement
- **Description**: The frontend MUST provide UI to set the user's preferred channel order, per-category channel overrides, a global pause toggle that stops all reminders while engaged, and per-channel consent toggles. Per-channel consent MUST be persisted as immutable consent grant/withdrawal events via the consent store (issue 045); the UI MUST NOT treat a channel as enabled for delivery unless an affirmative consent is recorded, and absence of consent MUST present as fail-closed (no delivery on that channel). Consent toggles MUST NOT be settable through any general preferences write — they are a distinct, audited action (no mass-assignment, `PRIV-1.15`).
- **Rationale**: Surfaces `FR-7.1` (channel order + per-category overrides), `FR-7.2` (global pause), and the consent half of `FR-6.2`/`PRIV-1.2`. Channel consent is a fail-closed gate on delivery; the UI must make granting/withdrawing explicit and never imply delivery without recorded consent.
- **Design**: Per `DESIGN.md` §7, preferences render as token-styled cards on Parchment; channel-order is a clear, keyboard-accessible reorder control; the global pause is a prominent toggle using DESIGN §6 voice ("The court rests…"). Consent toggles are visually distinct from ordinary preferences (they are audited, `PRIV-1.15`) and pair state with icon+label (not color alone, DESIGN §3.4). Focus uses the Gilt ring (DESIGN §7).

## Scope
- **Applies To**: Web App
- **Components**: React 19 SPA — channel-order control, per-category channel override editor, global pause toggle, per-channel consent toggles; consumes API client (057), Zod (056), component library (064), consent store API (045).
- **Actors**: Authenticated user (owner) configuring only their own notification preferences and consents.
- **Data Classification**: Restricted (consent records are Restricted; channel preferences tie to delivery of personal-data reminders).

## Security Context
- **Defense Layer**: Fail-closed authorization (consent gate) + Input Validation + no-mass-assignment.
- **Threat(s) Addressed**: Delivery on a non-consented channel (privacy violation, `FR-6.2`), consent set via mass-assignment through a preferences write (CWE-915, blocked by `PRIV-1.15`), continued delivery while paused. STRIDE: Tampering, Repudiation (mitigated by audited consent events), Information Disclosure.
- **Trust Boundary**: Client-server edge. Consent state and the pause gate are authoritative server-side (045, scheduler 031); the UI requests changes and reflects the recorded state but never asserts consent the server has not persisted.
- **Zero Trust Consideration**: The UI never assumes a channel is consented from a local toggle; effective consent is derived from the latest immutable server record (`PRIV-1.15`), and absence/indeterminacy fails closed to no delivery.

## Standards Alignment
- **OWASP ASVS**: V4 (access control), V5.1 (input validation), V8 (data protection)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: AC-3 (access enforcement), AU-2 (auditable consent events — server)
- **NIST SP 800-207**: fail-closed consent decision server-side
- **Regulatory**: GDPR Arts. 6, 7 (consent), 5(2) (accountability) — granular, withdrawable consent
- **Other**: `FR-7.1`, `FR-7.2`, `FR-6.2`, `PRIV-1.2`, `PRIV-1.15`

## Acceptance Criteria
1. **AC-01**: Given the preferences UI, when the user sets a preferred channel order and per-category overrides, then those are persisted and reflected. *(verbatim `FR-7.1`: the user MUST be able to set a preferred channel order and per-category channel overrides.)*
2. **AC-02**: Given the global pause toggle is engaged, when active, then the UI reflects that the scheduler enqueues and delivers no reminders while paused. *(verbatim `FR-7.2`: while paused the scheduler MUST NOT enqueue or deliver reminders.)*
3. **AC-03**: Given a per-channel consent toggle, when granted or withdrawn, then it is persisted as a distinct immutable consent event via 045 and the channel's delivery authorization is derived from the latest record.
4. **AC-04 (negative)**: Given a channel with no affirmative consent recorded, when its delivery state is shown, then the UI presents it as disabled/fail-closed (no delivery) — never as deliverable. *(verbatim `FR-6.2`: absence of consent MUST fail closed — no delivery on that channel.)*
5. **AC-05 (negative)**: Given a general preferences save, when submitted, then it cannot set or alter consent fields (no mass-assignment); consent changes require the distinct consent action. *(verbatim `PRIV-1.15`: consent fields MUST NOT be settable through any general contact or preferences write.)*
6. **AC-06 (accessibility)**: Given the preferences and consent controls, when rendered, then toggles/reorder are keyboard-operable with a visible Gilt focus ring, state is conveyed by text/icon not color alone, and contrast meets WCAG 2.2 AA (`NFR-1.4`, DESIGN §3.4).

## Failure Behavior
- **On Invalid Input**: Reject invalid channel-order/override input field-level; a consent change that the server cannot durably record fails closed (channel stays non-deliverable) and surfaces a gentle error.
- **On System Error**: Fail closed — if consent state cannot be confirmed, the UI shows the channel as not deliverable; if the pause state cannot be confirmed, it does not show reminders as resuming.
- **Alerting**: n/a at UI layer; consent grant/withdrawal is audited server-side (`SEC-8.1`, `PRIV-1.2`).

## Test Strategy
- **Unit Tests**: Channel-order and per-category override persist; pause toggle reflects paused state; consent toggle invokes the distinct consent action (045); a channel without consent renders disabled.
- **Integration Tests**: Grant then withdraw a channel consent and confirm two distinct events recorded (045) and delivery state flips fail-closed; engage pause and confirm scheduler stops (with 031/032).
- **Security Tests**: Attempt to set a consent field via a general preferences write and assert rejection (maps to PRIV-1.15 / no-mass-assignment); assert no-consent channel never presents as deliverable (maps to FR-6.2).
- **Compliance Tests**: Evidence that consent grant/withdrawal flows produce the auditable events required by `PRIV-1.2`.
- **Coverage Target**: ≥ 80% branch coverage of preferences and consent UI components.

## Dependencies
- **Upstream**: 054 (scaffold), 056 (Zod), 057 (API client), 064 (component library), 005 (tokens), 044 (notification preferences API), 045 (consent records store), 034 (channel consent enforcement), 026 (categories for per-category overrides).
- **Downstream**: 061 (reminder card channel reflects preferences/consent), 063 (privacy center shares the consent surface), 031/032 (scheduler honors pause + consent).
- **External**: None directly.

## Implementation Notes
- **Constraints**: Consent is a distinct, audited, fail-closed action (`PRIV-1.2`, `PRIV-1.15`) — never bundled into a preferences write. A channel is deliverable only with a recorded affirmative consent (`FR-6.2`). Pause stops all enqueue/delivery (`FR-7.2`). All styling via tokens (005).
- **Anti-Patterns**: MUST NOT show a non-consented channel as deliverable (`FR-6.2`); MUST NOT allow consent to be set via a general preferences write (`PRIV-1.15`); MUST NOT imply reminders resume before the server confirms unpause; MUST NOT mutate or backdate consent client-side (`PRIV-1.15`); MUST NOT hard-code styling (DESIGN §7.1).
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Preferences UI is conventional, broad work against a clear API contract. Human review must confirm the consent action is distinct from preferences writes (no mass-assignment) and that absent consent fails closed in the UI.
