# Requirement: Notification preferences — channel order, per-category overrides, global pause

## Metadata
- **ID**: REQ-DEL-044
- **Title**: Preferred channel order + per-category channel overrides + global pause (scheduler honors pause)
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Medium
- **Classification**: Functional

## Requirement
- **Description**: The user MUST be able to set a **preferred channel order** and **per-category channel overrides**, and MUST be able to **globally pause all reminders**. While paused the scheduler MUST NOT enqueue or deliver reminders. Preference writes MUST be validated against an explicit schema, rejected on failure with no coercion and no mass-assignment (consent fields are not settable here — consent is governed by the immutable consent store, issue 034 / `PRIV-1.15`), scoped to the owning user, and authorized per request. Channel preferences select **among channels for which affirmative consent is present**; a preferred/overridden channel without consent still fails closed at delivery (`FR-6.2`, issue 035) — a preference is not a consent.
- **Rationale**: Channel ordering and per-category overrides give the user control over how nudges arrive (`FR-7.1`); a global pause is the user's immediate "stop everything" control (`FR-7.2`). Honoring the pause in the scheduler (not merely the UI) ensures no reminder is enqueued or delivered while paused. Keeping preference separate from consent prevents a UI preference from being mistaken for a lawful basis to deliver.
- **Design**: Per `DESIGN.md` §6/§7, preferences live in a calm settings surface; the global pause is a single, clearly-labeled control with brand-voice confirmation ("The court rests"). Channels the user has not consented to are shown as unavailable, not silently ineffective.

## Scope
- **Applies To**: Both (Flask API preferences endpoints + React settings UI)
- **Components**: Preferences store (per-user, 010); validation framework (009); scheduler (issue 031/032 — reads pause + effective channel selection); consent store (034) for availability; audit log (012) for pause/override changes.
- **Actors**: Authenticated user (owner).
- **Data Classification**: Internal/Restricted (user preferences tied to the owning user; no contact PII).

## Security Context
- **Defense Layer**: Input Validation + Authorization (per-user scoping)
- **Threat(s) Addressed**: Mass-assignment / consent escalation via a preferences write (CWE-915, OWASP API3:2023), cross-user preference tampering (CWE-639), delivery on a non-consented preferred channel (mitigated by 035/`FR-6.2`). STRIDE: Tampering, Elevation of Privilege.
- **Trust Boundary**: Client→API edge; the API validates and scopes every preference write; the scheduler enforces the pause server-side, not the client.
- **Zero Trust Consideration**: A channel preference is never trusted as authorization to deliver — delivery still re-checks consent (`FR-6.2`); every write is validated server-side and user-scoped regardless of client state.

## Standards Alignment
- **OWASP ASVS**: V5.1 (input validation), V13/V11 (access control), V8 (data protection)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SI-10 (input validation), AC-3 (access enforcement), AC-4 (information flow — pause gating)
- **NIST SP 800-207**: per-request authorization inside the boundary
- **Regulatory**: GDPR Art. 7(3) (pause supports control over processing); Art. 25 privacy by default
- **Other**: `FR-7.1`, `FR-7.2`, `FR-6.2`, `PRIV-1.15`, `SEC-2.2`, SECURITY §4 (no mass-assignment)

## Acceptance Criteria
1. **AC-01**: Given an authenticated user, when they set a preferred channel order and a per-category channel override, then the preferences are saved, scoped to that user, and used to select the effective channel for matching reminders.
2. **AC-02 (`FR-7.2`)**: Given the user enables global pause, when the scheduler runs, then it enqueues and delivers no reminders for that user until pause is cleared.
3. **AC-03 (negative)**: Given a preference write containing an unknown field or a consent field, when submitted, then it is rejected (no mass-assignment) and no consent state changes (`PRIV-1.15`).
4. **AC-04 (negative)**: Given a preferred or per-category channel for which no affirmative consent exists, when a reminder targets it, then delivery fails closed on that channel (`FR-6.2`, issue 035) — the preference does not authorize delivery.
5. **AC-05 (negative)**: Given another user's preferences, when a user attempts to read or modify them, then the API returns not-found/forbidden and performs no write (`SEC-2.2`).

## Failure Behavior
- **On Invalid Input**: Reject with HTTP 400 and a field-level error; no partial write; no coercion (reject over sanitize).
- **On System Error**: Fail closed — if pause state cannot be determined, the scheduler treats the user as paused (no enqueue/deliver) rather than delivering on an unknown state; an indeterminate preference read defaults to the safest available consented channel order.
- **Alerting**: Repeated cross-user preference-access denials MAY raise an operational alert.

## Test Strategy
- **Unit Tests**: Preference schema validation; unknown/consent-field rejection; channel-order and per-category-override resolution; pause flag handling.
- **Integration Tests**: Set preferences and assert the scheduler selects the effective channel; enable pause and assert no enqueue/delivery; cross-user access denied.
- **Security Tests**: Mass-assignment attempt (consent/unknown field) rejected; cross-user read/write returns not-found/forbidden (maps to TEST-1.3 isolation).
- **Compliance Tests**: Pause and override changes are audited (`SEC-8.1`); a preferred-but-unconsented channel yields no delivery (TEST-1.4 consent fail-closed evidence).
- **Coverage Target**: ≥ 80% branch coverage of the preferences module.

## Dependencies
- **Upstream**: 009 (validation framework), 010 (per-user persistence), 012 (audit), 014 (authorization), 026 (categories — for per-category overrides), 034 (consent store — channel availability), 031/032 (scheduler reads pause + effective channel).
- **Downstream**: scheduler effective-channel selection; delivery worker (035) consumes the chosen channel (still consent-gated).
- **External**: None.

## Implementation Notes
- **Constraints**: Pause is enforced in the scheduler, not only the UI. Preference resolution selects only among consented channels; a preference is never treated as consent. All fields bounded per SECURITY §4; no mass-assignment.
- **Anti-Patterns**: MUST NOT let a channel preference authorize delivery without consent (`FR-6.2`); MUST NOT enqueue/deliver while paused; MUST NOT accept unknown/consent fields through this path; MUST NOT enforce pause client-side only.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Well-bounded preferences CRUD plus a scheduler pause gate against established validation/authz/scheduler frameworks; mechanical. Human review confirms preference-vs-consent separation and that pause is enforced server-side.
