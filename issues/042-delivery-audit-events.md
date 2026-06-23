# Requirement: Tamper-evident per-delivery audit events (fail closed, PII-minimal)

## Metadata
- **ID**: REQ-DEL-042
- **Title**: Append-only/hash-chained audit event per delivery attempt — reference, channel, consent-in-force, outcome, server time
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Medium
- **Classification**: Security

## Requirement
- **Description**: Each reminder delivery attempt MUST produce an **append-only / hash-chained** audit event (via the audit subsystem, issue 012) capturing the **reminder reference**, **target channel**, the **consent record in force**, the **outcome** (delivered, retried, dead-lettered), and a **server-authoritative timestamp** — sufficient to establish that delivery occurred on a consented channel within the allowed window. This event flow MUST **fail closed**: a delivery attempt whose outcome cannot be recorded MUST be treated as **not-delivered** (failed/dead-lettered), never silently completed. The event MUST NOT contain message content or personal data beyond the minimal reminder/contact reference and MUST be retention-bound (`SEC-8.2`, `FR-5.4`).
- **Rationale**: Delivery is the point where a consent decision becomes an action against a data subject; an immutable, attributable record that delivery happened on a consented channel within the window is the accountability evidence for GDPR Art. 5(2) and the `FR-6.2`/`FR-3.3` invariants. Fail-closed recording prevents a "delivered but unlogged" gap that would defeat accountability. Extends the SECURITY §6 audit trail specifically to delivery.
- **Design**: Per `DESIGN.md` minimal-payload posture (`FR-5.4`), the audit event references the reminder by id (the opaque id where applicable, issue 036) and never copies the contact display name or message body into the log.

## Scope
- **Applies To**: API / Backend (delivery worker → audit subsystem)
- **Components**: Delivery worker (035); audit subsystem (012, append-only/hash-chained); consent store (034); retention job (`PRIV-1.9`).
- **Actors**: Internal delivery worker (acting principal). Records are reviewed by an operator/auditor, never exposed to other users.
- **Data Classification**: Restricted (reminder/contact reference, consent-record id); Internal (channel, outcome, timestamp). No message content/PII.

## Security Context
- **Defense Layer**: Logging / tamper-evidence (accountability)
- **Threat(s) Addressed**: Repudiation of delivery, undetected delivery on withdrawn consent, log tampering (CWE-778 insufficient logging, CWE-117 log integrity). STRIDE: Repudiation, Tampering.
- **Trust Boundary**: The audit write shares the delivery commit boundary; a delivery that cannot be recorded is not allowed to be reported as completed.
- **Zero Trust Consideration**: Delivery success is not trusted unless durably and verifiably recorded; the timestamp is server-authoritative (client time MUST NOT be trusted, `SEC-8.3`), and the chain is independently verifiable (`SEC-8.5`).

## Standards Alignment
- **OWASP ASVS**: V7 (logging & error handling), V8 (data protection in logs)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: AU-2/AU-3/AU-9/AU-10/AU-12 (audit content, protection, non-repudiation, generation)
- **NIST SP 800-207**: continuous, verifiable record of access/action
- **Regulatory**: GDPR Art. 5(2) accountability, Art. 7(1) demonstrate consent
- **Other**: SECURITY §6, `SEC-8.1`, `SEC-8.2`, `SEC-8.3`, `FR-6.2`, `FR-3.3`, `NFR-1.2`, `FR-5.4`

## Acceptance Criteria
1. **AC-01**: Given a delivery attempt, when it completes, then an append-only/hash-chained audit event records the reminder reference, channel, consent-record-in-force, outcome, and a server-authoritative timestamp.
2. **AC-02**: Given a delivered reminder, when the audit trail is examined, then it shows delivery occurred on a channel with an active consent record at the delivery timestamp (`FR-6.2`/`PRIV-1.2` evidence).
3. **AC-03 (negative, fail closed)**: Given a delivery attempt whose audit outcome cannot be recorded, when processed, then the reminder is treated as not-delivered (failed/dead-lettered), not silently completed.
4. **AC-04 (negative)**: Given any delivery audit event, when inspected, then it contains no message content and no personal data beyond the minimal reminder/contact reference.
5. **AC-05 (negative)**: Given a client-supplied timestamp on a delivery event, when recorded, then the server-authoritative time is used and the client time is not trusted (`SEC-8.3`).

## Failure Behavior
- **On Invalid Input**: An event missing a required field is rejected by the audit subsystem; the delivery is treated as not-delivered.
- **On System Error**: Fail closed — if the audit write fails or the chain cannot be preserved, the delivery is not reported complete (routed to retry/DLQ via issue 041).
- **Alerting**: An audit-write failure on a delivery, or a chain-integrity break (`SEC-8.5`), MUST raise a security alert.

## Test Strategy
- **Unit Tests**: Event field set and PII-minimization; outcome mapping (delivered/retried/dead-lettered); server-time assignment; rejection of incomplete events.
- **Integration Tests**: Delivery produces an ordered, attributable, chained event; forced audit-write failure yields not-delivered, not silent success; consent-in-force is captured.
- **Security Tests**: Tamper/reorder a delivery audit entry → integrity check fails and alerts (consumes issue 012's verification); confirm no message content leaks into logs.
- **Compliance Tests**: For a delivered reminder, the consent history shows an active grant at the delivery timestamp (TEST-1.4 consent evidence); retention purge keeps the chain verifiable (`SEC-8.4`).
- **Coverage Target**: ≥ 80% branch coverage of the delivery-audit emission path.

## Dependencies
- **Upstream**: 012 (audit subsystem — append-only/hash-chain, server time, integrity verification), 034 (consent store), 035 (delivery worker), 041 (outcome states feed the event).
- **Downstream**: compliance/accountability reporting; retention job (`PRIV-1.9`).
- **External**: None (uses the internal audit subsystem).

## Implementation Notes
- **Constraints**: Reuses issue 012's tamper-evident store, server-authoritative time (`SEC-8.3`), and integrity verification (`SEC-8.5`); MUST NOT introduce a separate, weaker log. The event references the reminder by id (opaque id per 036 where applicable). Retention is `PRIV-1.9`/`SEC-8.4`-bound and MUST NOT break the chain on purge.
- **Anti-Patterns**: MUST NOT report a delivery complete without a durable audit record; MUST NOT copy contact display name or message body into the event; MUST NOT trust a client-supplied timestamp; MUST NOT delete/rewrite individual audit entries in a way that breaks the chain.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Bounded emission of a well-specified event against the established audit subsystem (012); mechanical once the chain/time primitives exist. Human review confirms fail-closed recording and PII minimization.
