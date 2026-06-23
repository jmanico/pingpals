# Requirement: Reminder actions — snooze, dismiss, mark-as-contacted

## Metadata
- **ID**: REQ-ENG-033
- **Title**: User can snooze, dismiss, or mark a reminder contacted; mark-as-contacted resets the cadence clock
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Functional

## Requirement
- **Description**: The user MUST be able to snooze, dismiss, or mark a reminder as contacted. Marking a reminder as contacted MUST reset the cadence clock for the underlying contact (reusing the last-contact logging path, issue 028). An active snooze MUST suppress further generation/delivery for that contact until the snooze expires (consumed by the scheduler, issue 031). All three actions MUST be authorized per-request and user-scoped, and MUST respect the global pause (`FR-7.2`, issue 044).
- **Rationale**: These are the user's controls over the reminder lifecycle (`FR-5.3`). Mark-as-contacted must reset cadence so the next reminder is correctly timed; routing it through the single last-contact logging path (issue 028) keeps the dual-timestamp and audit guarantees consistent.
- **Design**: Per `DESIGN.md` §5–§7, the reminder card offers snooze/dismiss/mark-contacted affordances; success copy is celebratory ("Decreed and done. Alex has been pinged. 👑").

## Scope
- **Applies To**: Both
- **Components**: Flask API reminder-action endpoints; React reminder card (DESIGN §7); per-user persistence (010); last-contact logging (028); scheduler snooze consumption (031); audit log (012); global pause (044).
- **Actors**: Authenticated user (owner).
- **Data Classification**: Restricted (reminder references a contact; mark-contacted creates a contact event).

## Security Context
- **Defense Layer**: Input Validation + Architecture (user-scoped state transitions)
- **Threat(s) Addressed**: Cross-user reminder manipulation (OWASP API1:2023), invalid state transition / replay, inconsistent cadence-reset path. STRIDE: Tampering, Elevation of Privilege.
- **Trust Boundary**: Client→API edge; reminder state transitions and cadence reset execute server-side.
- **Zero Trust Consideration**: Reminder ids are untrusted and resolved only within the owning user's data set; each action is per-request authorized; mark-contacted funnels through the server-authoritative time/audit path of issue 028.

## Standards Alignment
- **OWASP ASVS**: V5.1 (input validation), V13/V11 (access control), V7 (state transitions)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: AC-3, SI-10, AU-12
- **NIST SP 800-207**: per-request, user-scoped authorization
- **Regulatory**: GDPR Art. 5(2) accountability (via the audited contact event)
- **Other**: `FR-5.3`, `FR-7.2`, `SEC-8.1`

## Acceptance Criteria
1. **AC-01**: Given a reminder owned by the user, when they snooze it, then further generation/delivery for that contact is suppressed until the snooze expires (consumed by issue 031).
2. **AC-02**: Given a reminder owned by the user, when they dismiss it, then the reminder is resolved without resetting the cadence clock.
3. **AC-03 (verbatim `FR-5.3`)**: When a reminder is marked as contacted, then the cadence clock is reset (via issue 028's logging path).
4. **AC-04**: When any reminder action is taken, then a corresponding tamper-evident audit entry is written (`SEC-8.1`).
5. **AC-05 (negative)**: Given a reminder owned by another user, when an action is attempted, then the API returns not-found/forbidden and changes no state (`SEC-2.2`).
6. **AC-06 (negative)**: Given the account is globally paused, when the scheduler would act, then no reminders are enqueued or delivered (`FR-7.2`, issue 044).

## Failure Behavior
- **On Invalid Input**: Reject unknown/cross-user reminder id or invalid transition with not-found/forbidden/409; no state change.
- **On System Error**: Fail closed — if mark-contacted cannot record via the server-authoritative time/audit path, the cadence clock is not reset and the action is not applied.
- **Alerting**: Anomalous action rates MAY raise an operational signal.

## Test Strategy
- **Unit Tests**: Each action's state transition; snooze-expiry semantics; mark-contacted delegation to issue 028; dismiss does not reset cadence.
- **Integration Tests**: Snooze suppresses subsequent generation (with issue 031); mark-contacted resets cadence and writes a contact event + audit entry; global pause respected (issue 044).
- **Security Tests**: Cross-user action denied (TEST-1.3); replayed/invalid transition rejected.
- **Compliance Tests**: Audit entries present for each action; cadence-reset audited via the contact event.
- **Coverage Target**: ≥ 80% branch coverage of the reminder-action module.

## Dependencies
- **Upstream**: 010 (persistence), 012 (audit), 014 (authorization), 028 (last-contact logging path), 031 (scheduler consumes snooze).
- **Downstream**: 044 (notification preferences / global pause), delivery worker (later issue).
- **External**: None.

## Implementation Notes
- **Constraints**: Mark-as-contacted MUST reuse the single last-contact logging path (issue 028) so the dual-timestamp and audit guarantees are not duplicated or diverged. Snooze duration is bounded and validated. Respect global pause (issue 044) at scheduler/delivery time.
- **Anti-Patterns**: MUST NOT implement a second, divergent cadence-reset path; MUST NOT let dismiss silently reset cadence; MUST NOT act on a reminder without per-request, user-scoped authorization.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Bounded state-transition endpoints delegating to existing logging/audit paths; mechanical. Human review confirms mark-contacted reuses issue 028 and dismiss does not reset cadence.
