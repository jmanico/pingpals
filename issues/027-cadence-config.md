# Requirement: Cadence configuration with override precedence and fail-closed quiet hours/timezone

## Metadata
- **ID**: REQ-CON-027
- **Title**: Per-category and per-contact cadence, quiet hours, timezone — delivery window fails closed
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Functional

## Requirement
- **Description**: Cadence MUST be expressed as a positive interval in days and MAY also store a preferred day-of-week and a send-time window. A contact MUST inherit its category's default cadence unless a per-contact override is set, and a per-contact override MUST take precedence. The user MUST be able to set quiet hours and a timezone; reminders MUST NOT be delivered outside the allowed window; timezone resolution MUST **fail closed to no delivery** when the timezone is unknown.
- **Rationale**: Cadence and the allowed window are the inputs the scheduler evaluates (`FR-5.1`). Failing closed on an unknown timezone prevents delivering a reminder at an inappropriate local time (e.g., the middle of the night) when the window cannot be computed — a privacy-respecting, user-trust default (`FR-3.3`).
- **Design**: Per `DESIGN.md` §6, the product is "the calm confidence of a butler who never lets a birthday slip"; cadence/quiet-hours UI is generous, calm, and clear about when reminders will and will not arrive.

## Scope
- **Applies To**: Both
- **Components**: Flask API cadence/preference endpoints; React cadence + quiet-hours UI; category model (026); contact model (024); scheduler (031, consumer).
- **Actors**: Authenticated user (owner).
- **Data Classification**: Restricted (cadence/quiet-hours/timezone are user preference data tied to contacts).

## Security Context
- **Defense Layer**: Input Validation + Architecture (fail-closed window resolution)
- **Threat(s) Addressed**: Out-of-window delivery (privacy/trust harm), invalid interval/time injection (CWE-20), indeterminate-timezone fail-open. STRIDE: Tampering, Information Disclosure (untimely notification).
- **Trust Boundary**: Client→API edge; window/timezone resolution and override precedence computed server-side and re-checked at scheduler/delivery time.
- **Zero Trust Consideration**: Interval, day-of-week, window, and timezone are validated against explicit bounded schemas; an unresolvable timezone is treated as a fail-closed deny, not a default window.

## Standards Alignment
- **OWASP ASVS**: V5.1 (input validation), V7 (business logic)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SI-10, CM-7 (least functionality / restrictive defaults)
- **NIST SP 800-207**: indeterminate decision resolves to deny
- **Regulatory**: GDPR Art. 25 privacy by default
- **Other**: `FR-3.1`, `FR-3.2`, `FR-3.3`, ARCH Dependency Rule 3

## Acceptance Criteria
1. **AC-01**: Given a positive integer day interval (and optional preferred day-of-week and send-time window), when submitted, then it is accepted; a zero/negative/non-integer interval is rejected with a field-level error.
2. **AC-02**: Given a contact with no override, when its effective cadence is resolved, then it equals the category default; given a per-contact override, then the override takes precedence (`FR-3.2`).
3. **AC-03**: Given quiet hours and a timezone, when a reminder is due, then it is delivered only inside the allowed window (`FR-3.3`).
4. **AC-04 (verbatim `FR-3.3`)**: Given an unknown timezone, when window resolution runs, then it fails closed to no delivery (reminders MUST NOT be delivered outside the allowed window).
5. **AC-05 (negative)**: Given a quiet-hours window that would place delivery outside the allowed time, when the scheduler/delivery evaluates it, then no reminder is delivered in that window.

## Failure Behavior
- **On Invalid Input**: Reject with HTTP 400 and a field-level error; no partial write.
- **On System Error**: Fail closed — if cadence/window/timezone cannot be resolved, no reminder is generated or delivered for that contact.
- **Alerting**: A spike in fail-closed-no-delivery due to unresolved timezones MAY raise an operational alert (data-quality signal), without delivering.

## Test Strategy
- **Unit Tests**: Interval bounds (positive integer), override precedence resolution, window/quiet-hours computation, unknown-timezone fail-closed.
- **Integration Tests**: Effective-cadence resolution across category default + per-contact override; scheduler consumes the resolved window (issue 031).
- **Security Tests**: Malformed timezone/window inputs rejected; indeterminate timezone yields no delivery (maps to TEST-1.5 quiet-hours/timezone fail-closed).
- **Compliance Tests**: Evidence that no reminder is delivered outside the allowed window or under an unknown timezone.
- **Coverage Target**: ≥ 80% branch coverage of the cadence/window module.

## Dependencies
- **Upstream**: 009 (validation), 010 (persistence), 024 (contact), 026 (category default cadence).
- **Downstream**: 031 (scheduler cadence evaluation), 034 (channel consent enforcement at evaluation time), 044 (notification preferences / global pause).
- **External**: A timezone database (e.g., IANA tz) — vet per `SEC-9.x` before adding; treat an unresolved zone as fail-closed.

## Implementation Notes
- **Constraints**: Store timezone as an IANA identifier; compute windows server-side (do not trust client local time). Effective-cadence resolution is a pure function (category default vs. per-contact override) reused by the scheduler.
- **Anti-Patterns**: MUST NOT default an unknown timezone to UTC or to "deliver anyway"; MUST NOT accept a non-positive interval; MUST NOT let the client decide whether a reminder is in-window.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Deterministic interval/window logic with one clear fail-closed branch; well-bounded. Human review confirms unknown-timezone fail-closed and override precedence.
