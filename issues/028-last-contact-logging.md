# Requirement: Last-contact logging with distinct asserted vs. server record time

## Metadata
- **ID**: REQ-CON-028
- **Title**: Log contact event (mark contacted) resets cadence clock; asserted and server times stored separately
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Functional

## Requirement
- **Description**: The system MUST allow the user to log a contact event ("mark as contacted") with a timestamp defaulting to now, and logging MUST reset the cadence clock for that contact. The user-asserted event time and the immutable server-authoritative record time MUST be stored as **distinct fields**; the record time, not the asserted time, is the basis for tamper-evidence. The server record time MUST be assigned by a server-authoritative time source; if that source is unavailable or unverifiable, the record MUST be rejected (fail closed), not written with an untrusted time. The contact-event creation MUST be recorded in the tamper-evident audit log.
- **Rationale**: Marking a contact as contacted is what resets cadence (`FR-4.1`/`FR-4.2`); a user may legitimately backdate when they actually reached out. GDPR Art. 5(2) accountability and tamper-evidence require the immutable record time to be server-assigned and untrusted-client-time-free, while still preserving the user's asserted event time for accuracy (`SEC-8.3`).
- **Design**: Per `DESIGN.md` §5–§6, logging a contact on time is a celebratory moment ("Long live the streak!"); the UI lets the user confirm or adjust the asserted event time while the system silently records its own authoritative time.

## Scope
- **Applies To**: Both
- **Components**: Flask API contact-event endpoint; React "mark contacted" UI; per-user persistence (010); server time source; audit log (012); scheduler (031, consumer of the reset clock).
- **Actors**: Authenticated user (owner).
- **Data Classification**: Restricted (contact event ties to a contact; timestamps are accountability data).

## Security Context
- **Defense Layer**: Input Validation + Architecture (server-authoritative time, dual-timestamp model)
- **Threat(s) Addressed**: Client-time spoofing / audit backdating (CWE-345 insufficient verification of data authenticity), tamper-evidence bypass. STRIDE: Tampering, Repudiation.
- **Trust Boundary**: Client→API edge; the record time is assigned server-side and never accepted from the client.
- **Zero Trust Consideration**: The client-supplied event time is treated as an untrusted assertion stored in a separate field; only the server-authoritative time anchors tamper-evidence (`SEC-8.3`).

## Standards Alignment
- **OWASP ASVS**: V5.1 (input validation), V7/V9 (logging integrity)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: AU-8 (time stamps), AU-10 (non-repudiation), AU-12 (audit generation)
- **NIST SP 800-207**: untrusted-input handling inside the boundary
- **Regulatory**: GDPR Art. 5(2) accountability
- **Other**: `FR-4.1`, `FR-4.2`, `SEC-8.1`, `SEC-8.3`

## Acceptance Criteria
1. **AC-01**: Given an authenticated user, when they log a contact event with the default (now) timestamp, then a contact event is created and the contact's cadence clock is reset (`FR-4.2`).
2. **AC-02 (verbatim `SEC-8.3`)**: Given a contact event submitted with a past or future user-asserted time, when recorded, then the true server time is stored as the immutable record time and the asserted time is preserved in a separate field.
3. **AC-03 (verbatim `SEC-8.3`)**: Given a record submitted while the authoritative time source is unavailable, when processed, then the record is rejected.
4. **AC-04**: When a contact event is logged, then a corresponding tamper-evident audit entry is written in the same commit (`SEC-8.1`).
5. **AC-05 (negative)**: Given a client-supplied "record time" field, when submitted, then it is ignored/rejected and never used as the immutable record time (no mass-assignment of the authoritative timestamp).
6. **AC-06 (negative)**: Given a contact owned by another user, when a contact event is logged against it, then the API returns not-found/forbidden (`SEC-2.2`).

## Failure Behavior
- **On Invalid Input**: Reject with HTTP 400; no contact event written; no cadence reset.
- **On System Error**: Fail closed — if the authoritative time source is unavailable or the audit write fails, the event is not persisted and the cadence clock is not reset.
- **Alerting**: Authoritative-time-source unavailability MUST raise an operational alert (records are being rejected).

## Test Strategy
- **Unit Tests**: Default-now event creation; cadence-clock reset; dual-timestamp storage; client "record time" rejection; time-source-unavailable rejection.
- **Integration Tests**: Backdated and future-dated asserted times round-trip with a server record time; scheduler observes the reset clock (issue 031).
- **Security Tests**: Attempted backdating of the immutable record time is rejected; cross-user contact-event denied (TEST-1.3).
- **Compliance Tests**: Audit entry present for each contact event; asserted vs. record time evidenced for `SEC-8.3`.
- **Coverage Target**: ≥ 80% branch coverage of the contact-event module.

## Dependencies
- **Upstream**: 009 (validation), 010 (persistence), 012 (audit log + server time source), 014 (authorization), 024 (contact), 027 (cadence clock semantics).
- **Downstream**: 031 (scheduler reads last-contacted), 033 (mark-as-contacted reminder action reuses this reset).
- **External**: Server-authoritative time source (owned by audit subsystem 012); treat unavailability as fail-closed.

## Implementation Notes
- **Constraints**: The record time is sourced from the same server-authoritative time source as audit entries and consent records (`SEC-8.3`). The asserted time is bounded (no absurd far-past/far-future values) and validated. Mark-as-contacted via a reminder (issue 033) MUST funnel through this same reset logic.
- **Anti-Patterns**: MUST NOT use the client-asserted time as the tamper-evidence basis; MUST NOT write a record with an untrusted time when the authoritative source is down; MUST NOT reset the cadence clock without writing the audit entry.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Clear dual-timestamp model against an existing audit/time subsystem; mechanical once the fail-closed time-source branch is encoded. Human review confirms the record time is always server-assigned.
