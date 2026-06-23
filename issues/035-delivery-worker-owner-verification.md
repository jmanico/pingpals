# Requirement: Delivery-worker per-reminder owner + consent re-verification (fail closed)

## Metadata
- **ID**: REQ-DEL-035
- **Title**: Owning-user re-verification at send time; scheduler cross-user scope MUST NOT propagate to the delivery worker
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Critical
- **Classification**: Security

## Requirement
- **Description**: Every enqueued reminder MUST carry its owning user as a **non-optional** attribute, and the privileged cross-user scope under which the scheduler evaluates cadence MUST NOT propagate to the delivery worker. At send time the delivery worker MUST re-verify, **scoped to the reminder's owning user**, that the chosen channel and the resolved delivery endpoint (e.g. email address or push subscription) belong to that same user and that channel consent (`FR-6.2`) is still present. Any mismatch, indeterminate ownership, or absent consent MUST **fail closed**: the reminder MUST be dropped (not delivered) and the denial MUST be recorded in the tamper-evident audit log (issue 012).
- **Rationale**: The scheduler runs with a broad, cross-user read scope to evaluate every user's cadence (`NFR-1.1`); if that scope leaked into delivery, a corrupted or forged work item could route one user's reminder to another user's endpoint — a confidentiality and tenant-isolation breach (`SEC-2.2`). Re-verifying ownership and live consent at the send boundary makes the delivery worker a Zero-Trust consumer of its own queue (`SEC-2.1`, SECURITY §3 east-west rule) and enforces consent fail-closed (`FR-6.2`).
- **Design**: Per `DESIGN.md` §6, a dropped reminder is never surfaced as a delivered nudge; no user-facing error leaks another user's data. Delivery is silent on denial — the audit log, not the UI, is the record of the drop.

## Scope
- **Applies To**: API / Backend (delivery worker, queue consumer)
- **Components**: Delivery worker; reminder queue consumer; endpoint-ownership lookup (issue 037); consent store (issue 034); audit log (012); authorization decision point (014).
- **Actors**: Internal delivery worker (scoped service principal); Scheduler (producer). No human actor at send time.
- **Data Classification**: Restricted (owning-user id, delivery endpoint, consent record, contact reference).

## Security Context
- **Defense Layer**: Architecture (tenant isolation) + per-request/per-work-item Authorization
- **Threat(s) Addressed**: Cross-tenant data leakage / BOLA (OWASP API1:2023, CWE-639), confused-deputy via privileged scheduler scope (CWE-441), delivery on withdrawn consent (GDPR Art. 7). STRIDE: Spoofing (forged owning user), Information Disclosure, Elevation of Privilege.
- **Trust Boundary**: Scheduler→queue→delivery-worker internal boundary. The worker MUST NOT trust a work item on network position or producer identity alone (SECURITY §3, NIST SP 800-207); ownership is re-derived and re-authorized, not inherited.
- **Zero Trust Consideration**: Treats every dequeued reminder as untrusted: re-resolves the owning user, re-checks endpoint ownership and live consent against authoritative stores at send time, and denies on any indeterminacy rather than honoring the enqueued assertion.

## Standards Alignment
- **OWASP ASVS**: V13/V11 (object-level access control), V8 (authorization)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: AC-3 (access enforcement), AC-4 (information flow), AU-2/AU-12 (audit)
- **NIST SP 800-207**: per-request authorization inside the boundary; no implicit east-west trust
- **Regulatory**: GDPR Art. 5(1)(f) integrity & confidentiality, Art. 7 conditions for consent
- **Other**: `FR-5.5`, `FR-6.2`, `SEC-2.1`, `SEC-2.2`, `SEC-2.3`, `SEC-8.1`, ARCH Dependency Rule 4 & 8

## Acceptance Criteria
1. **AC-01**: Given an enqueued reminder with a present owning-user attribute, when the worker dequeues it and the resolved endpoint and live consent both belong to that user, then the reminder is handed to the channel adapter for delivery.
2. **AC-02 (verbatim `FR-5.5`)**: Given a reminder whose resolved delivery endpoint is owned by a different user, or whose ownership cannot be confirmed, when the worker processes it, then it is dropped rather than delivered, and an authorization-denial entry is written to the audit log.
3. **AC-03 (negative)**: Given a reminder whose channel consent (`FR-6.2`) has been withdrawn since enqueue, when the worker processes it, then it is dropped (no delivery) and the denial is audited.
4. **AC-04 (negative)**: Given a reminder enqueued without an owning-user attribute (schema-violating), when the worker dequeues it, then it is rejected/dead-lettered and never delivered; the scheduler's cross-user scope is not available to the worker to "look up" an owner.
5. **AC-05 (negative)**: Given a transient failure resolving ownership or consent (store timeout), when the worker processes the reminder, then it fails closed (drop/retry-bounded, never deliver) and never serves the decision from a degraded path (`SEC-2.3`).

## Failure Behavior
- **On Invalid Input**: A reminder missing the owning user, or failing schema, is rejected/dead-lettered; no delivery; audit entry recorded.
- **On System Error**: Fail closed — on any indeterminate ownership/consent decision the reminder is dropped, not delivered; bounded retry only where the indeterminacy is transient (see issue 041).
- **Alerting**: A nonzero rate of cross-user-ownership denials is security-significant and MUST raise an alert (potential forged-queue/compromise indicator).

## Test Strategy
- **Unit Tests**: Owning-user attribute required; ownership match/mismatch; consent present/withdrawn; indeterminate decision → deny.
- **Integration Tests**: End-to-end enqueue→deliver with matching owner (delivers) vs. mismatched/forged owner (dropped + audited); withdrawn consent between enqueue and send (dropped).
- **Security Tests**: Inject a reminder asserting a foreign owning user / pointing at a foreign endpoint; assert no delivery and an audited denial (maps to TEST-1.3 cross-user isolation; complements SECURITY §3 forged-internal-message test in issue 016).
- **Compliance Tests**: Audit log shows an attributable authorization-denial entry per dropped reminder (`SEC-8.1`); consent fail-closed evidence (TEST-1.4).
- **Coverage Target**: ≥ 80% branch coverage of the delivery-worker authorization path.

## Dependencies
- **Upstream**: 010 (per-user persistence/scoping), 012 (audit log), 014 (authorization decision point), 016 (internal message authentication), 034 (consent store), 037 (delivery-endpoint ownership), queue/broker decision issue.
- **Downstream**: 036 (payload confidentiality), 040 (web-push adapter), 041 (retry/circuit breaker), 042 (delivery audit events).
- **External**: None directly; relies on the chosen durable queue (decision issue) and KMS for endpoint decryption (011).

## Implementation Notes
- **Constraints**: The worker MUST run under a service principal scoped per-reminder to the owning user; it MUST NOT hold the scheduler's cross-user read grant. Ownership and consent are re-derived from authoritative stores, never read from the enqueued payload as truth. Queue/broker is `TO BE DECIDED` — keep the consumer behind an interface and default to deny on any unverifiable work item.
- **Anti-Patterns**: MUST NOT inherit or impersonate the scheduler's broad scope in the worker; MUST NOT trust the owning-user field as authoritative without re-resolving the endpoint against it; MUST NOT deliver on an indeterminate consent/ownership decision; MUST NOT silently swallow a drop without an audit entry.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** A subtle scope-propagation or fail-open mistake here is a directly exploitable cross-tenant breach; favor the strongest adversarial reasoning on privilege boundaries and fail-closed logic. Mandatory human security review before merge.
