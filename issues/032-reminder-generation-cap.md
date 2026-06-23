# Requirement: Per-user reminder generation cap per scheduler window

## Metadata
- **ID**: REQ-ENG-032
- **Title**: Scheduler caps reminders per user per window to prevent runaway generation and notification flooding
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Security

## Requirement
- **Description**: The scheduler MUST cap the number of reminders generated per user per scheduler window to prevent runaway delivery and notification flooding. When the cap is reached for a user in a window, the scheduler MUST stop generating further reminders for that user in that window (fail closed) and MUST record that the cap was hit, without dropping data integrity for the next window.
- **Rationale**: Even with a bounded contact set, a misconfiguration or edge case could attempt to generate a large burst of reminders for one user; the per-user per-window cap (`SEC-6.2`) bounds notification volume and protects shared delivery capacity from one account flooding the system.
- **Design**: Per `DESIGN.md` §6, the product is a calm advisor, not a nag; the cap operationalizes that — reminders never arrive as a flood.

## Scope
- **Applies To**: API (internal background service)
- **Components**: Scheduler service (031); per-user counter/state for the current window; audit/metrics (012).
- **Actors**: Scheduler (internal service), per owning user.
- **Data Classification**: Restricted (reminders reference contacts); the cap counter itself is internal/aggregate.

## Security Context
- **Defense Layer**: Architecture (resource/volume bounding, fail-closed cap)
- **Threat(s) Addressed**: Runaway reminder generation / notification flooding (CWE-770 allocation without limits), shared-capacity exhaustion by one user. STRIDE: Denial of Service.
- **Trust Boundary**: Internal east-west — the cap is enforced inside the boundary against the asserted owning user, never trusting volume to self-limit.
- **Zero Trust Consideration**: The cap is enforced server-side per user; no input can raise a user's cap; reaching the cap fails closed (stop generating).

## Standards Alignment
- **OWASP ASVS**: V11 (anti-automation), V7 (business logic)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SC-5 (DoS protection), SC-6 (resource availability)
- **NIST SP 800-207**: fail-closed on resource boundary
- **Regulatory**: n/a (operational abuse control)
- **Other**: `SEC-6.2`; distinct from delivery-path retry control (issue 041, `NFR-1.5`)

## Acceptance Criteria
1. **AC-01 (verbatim `SEC-6.2`)**: Given a user and a scheduler window, when reminders are generated, then the count per user per window is capped to prevent runaway delivery and notification flooding.
2. **AC-02**: Given a user reaches the per-window cap, when the scheduler continues, then no further reminders are generated for that user in that window (fail closed).
3. **AC-03**: Given the cap was hit in a window, when the cap event occurs, then it is recorded (metric/audit) for operational visibility.
4. **AC-04**: Given the next scheduler window begins, when evaluation resumes, then the cap counter resets and previously deferred-but-still-due reminders are evaluated normally (no permanent starvation).
5. **AC-05 (negative)**: Given any request or work item, when it attempts to raise the per-user cap, then the cap is not modified (server-enforced, not client-controllable).

## Failure Behavior
- **On Invalid Input**: n/a (internal); a work item cannot alter the cap.
- **On System Error**: Fail closed — if the per-user counter cannot be read, treat the user as at-cap for that window rather than generating unbounded.
- **Alerting**: Hitting the cap for a user MUST raise an operational alert (likely misconfiguration or abuse).

## Test Strategy
- **Unit Tests**: Counter increment/reset per window; cap-reached stop condition; counter-read-failure fail-closed.
- **Integration Tests**: Simulate a user whose due reminders exceed the cap → generation stops at the cap, resumes next window; assert no flood.
- **Security Tests**: Confirm no input path raises the cap; confirm the cap is independent of the delivery-path retry control (issue 041).
- **Compliance Tests**: Cap-hit events present in metrics/audit.
- **Coverage Target**: ≥ 80% branch coverage of the cap logic.

## Dependencies
- **Upstream**: 031 (scheduler cadence evaluation), 012 (audit/metrics), 013 (rate-limiting framework, related).
- **Downstream**: Delivery worker (later issue), 041 (delivery-path retry/circuit-breaker — distinct concern).
- **External**: Per-window counter store (`TO BE DECIDED`) — keep behind an interface, default to fail-closed at-cap.

## Implementation Notes
- **Constraints**: The cap is configurable with a most-restrictive default; counter is scoped per (user, window). This is **generation-side** flooding control and is explicitly distinct from delivery-path retry/dead-letter/circuit-breaking (issue 041, `NFR-1.5`). Still-due reminders are not lost — they are re-evaluated in the next window.
- **Anti-Patterns**: MUST NOT let one user's volume affect another's; MUST NOT permanently starve a user whose due count exceeds one window's cap; MUST NOT conflate this with delivery retries.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** A focused counter/threshold control on top of the scheduler; mechanical once the per-window reset and fail-closed-at-cap rules are clear. Human review confirms separation from delivery-path retry control.
