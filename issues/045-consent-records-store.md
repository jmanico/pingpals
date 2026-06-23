# Requirement: Append-only immutable consent event store

## Metadata
- **ID**: REQ-PRIV-045
- **Title**: Append-only immutable per-channel consent event store with fail-closed authorization
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Critical
- **Classification**: Compliance

## Requirement
- **Description**: The system MUST persist user consent as an append-only, immutable event log in which every consent grant and every consent withdrawal is a distinct event capturing a server-authoritative timestamp, the affected channel/scope, the notice version, and a link to the consent it establishes or revokes. An existing consent record MUST NOT be edited, deleted (outside erasure per `PRIV-1.6`), or have its timestamp or scope backdated. The effective consent state for any channel at any past instant MUST be derivable from this event history; where it cannot be determined unambiguously, delivery on that channel MUST fail closed (`FR-6.2`). Per-channel delivery authorization MUST be evaluated **only** from the latest immutable consent record for that channel and MUST fail closed if record integrity cannot be established. Consent fields MUST NOT be settable through any general contact or preferences write (the no-mass-assignment rule). All consent-change events MUST be carried in the tamper-evident audit trail (`SEC-8.1`).
- **Rationale**: GDPR Article 7(1) requires the controller to *demonstrate* consent; Article 5(2) accountability requires that demonstration to be tamper-evident and time-true. A mutable or backdatable consent record destroys the legal evidentiary value and would let a delivery be authorized on a channel the user never consented to. This is the data-of-record behind `PRIV-1.2`, `PRIV-1.15`, and the consent half of `FR-6.2`.
- **Design**: Per `DESIGN.md` §6, consent prompts and withdrawals are presented in the gentle royal voice, but the recorded event is purely structured data. The store is presentation-agnostic; UI consumes a derived "current consent state per channel" view, never the raw write path.

## Scope
- **Applies To**: API
- **Components**: Privacy/DSR subsystem — ConsentRecord store; consumed by Delivery worker (consent gate), Scheduler (`FR-5.1`), and audit subsystem (012).
- **Actors**: Authenticated user (owner, sole consent principal); Delivery worker (read-only consent evaluator); Scheduler (read-only).
- **Data Classification**: Restricted (consent records, per §3 data classification).

## Security Context
- **Defense Layer**: Architecture (immutable event store) + Strict API (no mass-assignment) + Input Validation
- **Threat(s) Addressed**: Repudiation of consent state, tampering/backdating of consent records, mass-assignment privilege escalation into consent fields (CWE-915), fail-open delivery on indeterminate consent. STRIDE: Tampering, Repudiation, Elevation of Privilege.
- **Trust Boundary**: API service — the consent write path is the only authority that may append a consent event; it is segregated from the general contact/preferences write path so no bulk update can touch consent fields.
- **Zero Trust Consideration**: Delivery authorization derives consent live from the latest immutable record on every send; no cached "user consented once" assumption is trusted, and an unreadable/integrity-failed record denies rather than defaults to allow.

## Standards Alignment
- **OWASP ASVS**: V5.1 (input validation, no mass-assignment), V7.x (logging/audit integrity)
- **OWASP AISVS**: n/a (no AI component)
- **NIST SP 800-53**: AU-10 (non-repudiation), AC-3 (access enforcement), SI-10 (input validation)
- **NIST SP 800-207**: per-request, fail-closed authorization decision from authoritative state
- **Regulatory**: GDPR Arts. 5(2), 6(1)(a)/(f), 7(1)–7(3) (demonstrate and withdraw consent)
- **Other**: `PRIV-1.2`, `PRIV-1.15`, `FR-6.2`, `SEC-8.1`, `SEC-8.3`; SECURITY.md §4 (no mass-assignment), §9

## Acceptance Criteria
1. **AC-01**: Given a user grants then withdraws consent for a channel, when the events are persisted, then two distinct, ordered, linked events exist — each carrying a server-authoritative timestamp, the affected channel/scope, and the notice version — and both appear as distinct entries in the tamper-evident audit trail (012).
2. **AC-02 (verbatim `PRIV-1.2`)**: Given any delivered reminder, when the consent history is inspected, then it shows an active grant for the chosen channel with no intervening withdrawal at the delivery timestamp.
3. **AC-03 (verbatim `PRIV-1.15`)**: Given an attempt to edit or backdate an existing consent record, when processed, then it is rejected; delivery is authorized solely from the latest immutable record; and a missing or integrity-failed record yields no delivery on that channel.
4. **AC-04 (negative)**: Given a general contact or preferences write whose payload includes consent fields, when processed, then the consent fields are rejected/ignored (no mass-assignment) and no consent event is created.
5. **AC-05 (negative)**: Given a channel whose consent state cannot be unambiguously derived from history (ambiguous or integrity-failed), when a reminder is evaluated for that channel, then delivery fails closed (no send) and the denial is recorded (012).

## Failure Behavior
- **On Invalid Input**: Reject the consent write with HTTP 422 and a field-level error; no partial write. A mass-assignment attempt into consent fields is rejected, not silently dropped.
- **On System Error**: Fail closed — if the consent store or its integrity check is unavailable/indeterminate, the affected channel is treated as not-consented (no delivery), per `SEC-2.3`/`FR-6.2`.
- **Alerting**: A detected integrity failure on a consent record, or an attempted backdate/edit, MUST raise a tamper alert (ties to 012 / `SEC-8.5`).

## Test Strategy
- **Unit Tests**: Event append/link logic; derivation of effective state at an arbitrary past instant; rejection of edit/delete/backdate; rejection of consent fields via general write; notice-version capture.
- **Integration Tests**: Grant→withdraw→re-grant sequence drives correct per-channel authorization at the Delivery worker; ambiguous history fails closed (consumed by 058/delivery worker and 052).
- **Security Tests**: Mass-assignment fuzz across contact/preferences endpoints asserting no consent mutation; tamper test mutating a stored consent record is detected (maps to TEST-1.4 consent fail-closed).
- **Compliance Tests**: Automated evidence that for a sample of deliveries, an active grant existed at the delivery timestamp with no intervening withdrawal (GDPR Art. 5(2) accountability).
- **Coverage Target**: ≥ 80% branch coverage of the consent module.

## Dependencies
- **Upstream**: 010 (persistence + user scoping), 011 (KMS encryption at rest), 012 (tamper-evident audit log), 014 (authorization decision point), 009 (input validation framework, no mass-assignment).
- **Downstream**: 058/Delivery worker (consent gate at send), 050 (DSR endpoints surface consent), 046 (export includes consent records), 048 (erasure cascades consent records), 051 (retention/accountability period for consent events), 052 (privacy-by-default channel state).
- **External**: None (managed key store via 011 interface; KMS vendor `TO BE DECIDED` → DECISION 072).

## Implementation Notes
- **Constraints**: Append-only storage with a hash-chain or equivalent shared with 012; server-authoritative time only (`SEC-8.3`) — a record submitted while the authoritative time source is unavailable is rejected. Consent write path is a dedicated, narrowly-scoped endpoint.
- **Anti-Patterns**: MUST NOT model consent as a mutable boolean column updated in place; MUST NOT allow consent fields in any bulk/preferences update (no mass-assignment); MUST NOT trust a client-supplied timestamp; MUST NOT default an indeterminate channel to "consented".
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Immutable evidentiary data model with fail-closed legal consequences and mass-assignment hazards — favor the strongest adversarial reasoning on state-derivation and tamper edge cases. Mandatory human privacy/security review before merge; keep the audit-chain shape in sync with issue 012.
