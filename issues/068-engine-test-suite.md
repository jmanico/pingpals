# Requirement: Reminder-engine test suite (idempotency, cadence boundaries, quiet-hours/timezone fail-closed)

## Metadata
- **ID**: REQ-TEST-068
- **Title**: Mandatory reminder-engine test cases for the TEST-1.5 control set
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Functional

## Requirement
- **Description**: The test suite MUST include reminder-engine test cases that cover, at minimum: reminder-generation idempotency (`FR-5.2`), cadence boundary conditions (the `now − last_contacted ≥ effective_cadence` edge per `FR-5.1`/`FR-3.1`/`FR-3.2`), and quiet-hours plus timezone fail-closed behavior (`FR-3.3`). Each MUST have explicit positive and negative cases and MUST run in CI on the harness (issue 065) as part of the blocking gate (issue 003).
- **Rationale**: `TEST-1.5` enumerates exactly these engine areas as mandatory coverage. The scheduler is the system's core behavior; idempotency prevents duplicate/runaway reminders, boundary tests pin the cadence semantics, and timezone fail-closed prevents delivery outside the user's allowed window.
- **Design**: Per `DESIGN.md`, no end-user UI; tests assert scheduler/worker behavior. Test payloads MUST honor the minimal-payload rule (`FR-5.4`) and contain no PII in logs (`SEC-8.2`).

## Scope
- **Applies To**: Both (engine is backend; e2e may assert the resulting reminder surfaces correctly in the SPA)
- **Components**: Scheduler service (031), reminder-generation cap (032), cadence config (027), last-contact logging (028), reminder actions/snooze (033), channel-consent gate (034).
- **Actors**: The scheduler (internal); the owning user (sets cadence, quiet hours, timezone, snooze).
- **Data Classification**: Restricted (contact cadence/last-contacted are personal data — synthetic in tests).

## Security Context
- **Defense Layer**: Architecture / Verification (asserts fail-closed and idempotency invariants of the engine).
- **Threat(s) Addressed**: Duplicate/runaway reminder generation (notification flooding, resource exhaustion — ties `SEC-6.2`), delivery outside the allowed window on unknown timezone (privacy/UX harm), off-by-one cadence errors. STRIDE: Denial of Service, Tampering (clock/timezone manipulation).
- **Trust Boundary**: Exercises the scheduler→delivery path and the timezone-resolution decision point; verifies fail-closed.
- **Zero Trust Consideration**: Timezone resolution and consent are evaluated per generation; an unknown timezone or indeterminate window resolves to no delivery rather than a permissive default.

## Standards Alignment
- **OWASP ASVS**: V11.x (business logic / anti-automation), V7.x (error handling for fail-closed)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SI-10 (input validation of cadence/timezone), SC-5 (denial-of-service protection via generation cap), SA-11 (developer testing)
- **NIST SP 800-207**: deny-by-default for indeterminate timezone/window
- **Regulatory**: GDPR Art. 5(1)(c) data minimization (minimal reminder payload, `FR-5.4`)
- **Other**: `TEST-1.5`, `FR-5.1`, `FR-5.2`, `FR-3.1`, `FR-3.2`, `FR-3.3`, `SEC-6.2`

## Acceptance Criteria
[Each criterion MUST be independently testable.]

1. **AC-01 (idempotency)**: Given a single due event, when the scheduler re-runs for the same window, then no additional reminders are produced. *(verbatim `FR-5.2`: re-running the scheduler for the same window produces no additional reminders.)*
2. **AC-02 (cadence boundary)**: Given `now − last_contacted` exactly equal to the effective cadence, when evaluated, then a reminder is generated (`≥` boundary is inclusive per `FR-5.1`); given one unit below the cadence, then no reminder is generated.
3. **AC-03 (per-contact override precedence)**: Given a contact with a per-contact cadence override differing from its category default, when evaluated, then the override governs. *(maps to `FR-3.2`: a per-contact override MUST take precedence.)*
4. **AC-04 (quiet hours / timezone fail-closed)**: Given a contact due but the current time outside the allowed send window, or with an unknown/unresolvable timezone, when evaluated, then no reminder is delivered. *(verbatim `FR-3.3`: reminders MUST NOT be delivered outside the allowed window; timezone resolution MUST fail closed to no delivery when the timezone is unknown.)*
5. **AC-05 (negative — no consent / active snooze)**: Given a due contact whose channel consent is absent or that has an active snooze, when evaluated, then no reminder is generated (all `FR-5.1` conjuncts required).
6. **AC-06 (negative — generation cap)**: Given a user exceeding the per-user per-window reminder cap, when the scheduler runs, then generation is bounded and does not exceed the cap. *(maps to `SEC-6.2`.)*
7. **AC-07 (negative — coverage)**: Given the suite, when run in CI, then absence of any of the three mandated case groups (idempotency, cadence boundary, quiet-hours/timezone) fails the build.

## Failure Behavior
- **On Invalid Input**: A failing engine assertion fails the CI gate and blocks merge.
- **On System Error**: Fail closed — an errored or skipped engine test counts as a failure; the engine under test itself fails closed (no delivery) on unknown timezone.
- **Alerting**: A regression in any TEST-1.5 case raises a gate failure on the PR.

## Test Strategy
- **Unit Tests**: Effective-cadence resolver (category default vs. per-contact override); due-predicate at the `≥` boundary (off-by-one table); timezone/window resolver fail-closed on unknown zone; idempotency-key derivation.
- **Integration Tests**: Run the scheduler twice over the same window and assert no duplicate reminders (idempotency); run with consent absent / snooze active / out-of-window and assert zero deliveries; run with a user over the cap and assert bounding.
- **Security Tests**: Inject ambiguous/invalid timezone and DST-edge timestamps; assert fail-closed; attempt to force duplicate generation via concurrent runs.
- **Compliance Tests**: CI evidence that all three TEST-1.5 groups executed and passed; reminder payloads asserted minimal (`FR-5.4`).
- **Coverage Target**: ≥80% branch coverage of engine-test helpers; the cadence-boundary table MUST cover the exact-equal, just-below, and just-above cases.

## Dependencies
- **Upstream**: 065 (harness/coverage gate), 027 (cadence config), 028 (last-contact logging), 031 (scheduler), 032 (generation cap), 033 (reminder actions/snooze), 034 (channel-consent gate); time source per `SEC-8.3`.
- **Downstream**: 003 (CI gate); the reliability of all delivery (035–042) depends on the engine behaving per these tests.
- **External**: A deterministic/injectable clock and timezone database (vetted per `SEC-9.1`).

## Implementation Notes
- **Constraints**: Tests MUST control the clock deterministically and exercise DST transitions explicitly. Idempotency tests MUST cover concurrent/overlapping scheduler runs, not just sequential re-runs. The boundary is `≥` (inclusive) per `FR-5.1` — pin this exactly.
- **Anti-Patterns**: MUST NOT rely on wall-clock time in tests (flaky, non-deterministic); MUST NOT assert only that reminders are generated (the no-delivery negatives are the security-relevant cases); MUST NOT treat an unknown timezone as "use UTC" — that violates `FR-3.3` fail-closed.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** This is well-specified deterministic logic (boundary tables, idempotency keys, timezone/DST cases) where systematic enumeration and broad familiarity with date/time pitfalls is the main asset; novel adversarial reasoning is limited. Human review confirms the `≥` boundary and DST-edge cases match `FR-5.1`/`FR-3.3` before merge.
