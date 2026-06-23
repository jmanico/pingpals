# Requirement: Scheduler cadence evaluation — idempotent, bounded, horizontally scalable

## Metadata
- **ID**: REQ-ENG-031
- **Title**: Scheduler emits a reminder when cadence elapsed AND in-window AND consent present AND not snoozed; idempotent generation
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Critical
- **Classification**: Functional

## Requirement
- **Description**: The scheduler MUST generate a reminder for a contact when **all** of the following hold: `now − last_contacted ≥ effective_cadence` AND the current time is within the allowed send window AND the required channel consent is present AND no active snooze exists. Reminder generation MUST be **idempotent** — a single due event MUST NOT produce duplicate reminders, enforced by an idempotency key, such that re-running the scheduler for the same window produces no additional reminders. Evaluation MUST be horizontally scalable across users (by user shard) and the per-window evaluation cost per user MUST stay bounded (`NFR-1.1`).
- **Rationale**: This is the core engine condition (`FR-5.1`). Idempotency (`FR-5.2`) is essential because the scheduler is re-runnable and may overlap windows; without an idempotency key a user would be flooded with duplicate reminders. Horizontal scalability and bounded per-window cost keep one user from degrading the engine for others (`NFR-1.1`, bounded by the contact quota in issue 029).
- **Design**: Per `DESIGN.md`, reminders are gentle nudges; the engine's job is correct, non-duplicative timing, never volume.

## Scope
- **Applies To**: API (internal background service)
- **Components**: Scheduler service; effective-cadence resolution (027); channel-consent check (034); snooze state (033); durable reminder queue (`[ASSUMPTION]`, TBD); idempotency-key store; audit log (012).
- **Actors**: Scheduler (internal service); operates per owning user — never cross-user beyond its evaluation scope.
- **Data Classification**: Restricted (operates over contacts, cadence, consent, last-contacted).

## Security Context
- **Defense Layer**: Architecture (idempotent, bounded, user-sharded evaluation; fail-closed conditions)
- **Threat(s) Addressed**: Duplicate/runaway reminder generation (CWE-770), cross-user leakage in batch evaluation (OWASP API1:2023), notification flooding, unbounded per-window cost. STRIDE: Denial of Service, Information Disclosure.
- **Trust Boundary**: Internal east-west — Zero Trust applies inside the boundary; each work item is authorized against its asserted owning user before any action and never trusted on network position (SECURITY §3).
- **Zero Trust Consideration**: Each reminder carries its owning user as a non-optional attribute; the scheduler evaluates strictly within a user's data set and resolves indeterminate consent/timezone to deny (no generation).

## Standards Alignment
- **OWASP ASVS**: V7 (business logic), V11 (anti-automation/resource bounding)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SC-5 (DoS protection), AC-3, AU-12
- **NIST SP 800-207**: per-work-item authorization inside the boundary; fail-closed on indeterminate decisions
- **Regulatory**: GDPR Art. 25 privacy by default (consent-gated generation)
- **Other**: `FR-5.1`, `FR-5.2`, `NFR-1.1`, `SEC-6.2` (cap in issue 032), ARCH Dependency Rule 8

## Acceptance Criteria
1. **AC-01**: Given a contact where `now − last_contacted ≥ effective_cadence`, the current time is within the allowed send window, the required channel consent is present, and no active snooze exists, when the scheduler runs, then exactly one reminder is generated.
2. **AC-02 (verbatim `FR-5.2`)**: Given a single due event, when the scheduler is re-run for the same window, then it produces no additional reminders (idempotent — no duplicates).
3. **AC-03**: Given any one of the four conditions is false (cadence not elapsed, out of window, consent absent, or active snooze), when the scheduler runs, then no reminder is generated for that contact.
4. **AC-04 (verbatim `NFR-1.1`)**: Given any user, when the scheduler evaluates, then the per-window evaluation cost remains bounded (by the contact quota, issue 029) and evaluation is horizontally scalable across users.
5. **AC-05 (negative)**: Given an unknown timezone or indeterminate channel consent, when the scheduler runs, then it fails closed and generates no reminder (`FR-3.3`, `FR-6.2`).
6. **AC-06 (negative)**: Given an internal work item asserting an owning user it is not authorized for, when processed, then it is rejected and dead-lettered and produces no reminder (SECURITY §3).

## Failure Behavior
- **On Invalid Input**: A malformed/unauthorized work item is rejected and dead-lettered (issue 016); no reminder generated.
- **On System Error**: Fail closed — indeterminate consent/timezone or a dependency timeout yields no generation (`SEC-2.3`, `NFR-1.6`); bounded retry, no unbounded loop.
- **Alerting**: Idempotency-key collisions beyond expected, or per-window cost exceeding budget, MUST raise an operational alert.

## Test Strategy
- **Unit Tests**: The four-part condition; idempotency-key generation/dedup; cadence boundary (just-below vs. at-or-above the interval).
- **Integration Tests**: Re-run the scheduler over the same window → no additional reminders (TEST-1.5 idempotency); fail-closed on unknown timezone / absent consent (TEST-1.5).
- **Security Tests**: Cross-user evaluation isolation; forged/replayed internal work item rejected (SECURITY §3).
- **Compliance Tests**: Consent-present-at-generation evidenced; bounded per-window cost under load.
- **Coverage Target**: ≥ 80% branch coverage of the scheduler module.

## Dependencies
- **Upstream**: 010 (persistence), 012 (audit log), 016 (internal message authn), 027 (effective cadence + window), 029 (contact quota bound), 033 (snooze state), 034 (channel consent enforcement).
- **Downstream**: 032 (per-user generation cap), delivery worker + per-reminder delivery audit (later issues), 041 (delivery-path retry control).
- **External**: Durable reminder queue (`TO BE DECIDED`); idempotency-key store (`TO BE DECIDED`) — keep behind interfaces, default to fail-closed dedup.

## Implementation Notes
- **Constraints**: Idempotency key is derived from (user, contact, due-window) so re-evaluation dedupes. The per-user generation **cap** is a distinct concern owned by issue 032 (`SEC-6.2`). Evaluation is sharded by user for horizontal scale. **Split recommendation:** if the module exceeds ~1500 LOC, extract the idempotency-key store/dedup into a separate module/issue, keeping the condition-evaluation core focused.
- **Anti-Patterns**: MUST NOT generate without an idempotency key; MUST NOT trust an internal work item on network position; MUST NOT fail open on indeterminate consent/timezone; MUST NOT evaluate across users in a single unscoped pass.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** The idempotency + multi-condition + fail-closed + bounded-cost intersection is the highest-correctness-risk part of the engine; subtle boundary or dedup errors cause floods or silent misses. Mandatory human review of the idempotency key and the fail-closed branches.
