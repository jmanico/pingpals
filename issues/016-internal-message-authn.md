# Requirement: Internal message and service-to-service authentication (zero trust inside the boundary)

## Metadata
- **ID**: REQ-BE-016
- **Title**: Producer-authenticated, per-item-authorized internal messages for Scheduler/Delivery/queue
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Security

## Requirement
- **Description**: The Scheduler, Delivery worker, and any queue consumer MUST NOT trust a peer or a work item on the basis of network position. Internal service-to-service calls and queue messages MUST be authenticated to their producer (for example mTLS or a signed/MAC'd envelope — the concrete mechanism follows the chosen queue/transport, DECISION 070), and every work item MUST be authorized against its asserted owning user before any action, exactly as the API authorizes a request. An internal message that is unauthenticated, fails integrity/replay checks, or cannot be authorized to a valid owning user MUST fail closed — rejected and dead-lettered, never processed. This is distinct from external webhook signature verification (`SEC-7.1`), which governs inbound third-party callbacks.
- **Rationale**: Anchored in SECURITY.md §3 (Zero Trust inside the boundary), `SEC-2.1`/`SEC-2.2` (per-request/per-item authorization, user scoping), `SEC-2.3` (fail closed), ARCH Dependency Rule 8 (Scheduler→Delivery idempotent and authorized). The "single trust boundary" framing for the API must not be read as implicit trust of east-west traffic; a forged or replayed queue message could otherwise cause a delivery to the wrong user or a privilege jump from the Scheduler's cross-user evaluation scope (`FR-5.5`).
- **Design**: No user-facing surface; underpins the FR-5.5 guarantee that the Delivery worker re-verifies ownership/consent before sending.

## Scope
- **Applies To**: API (internal services/workers within the deployment).
- **Components**: Scheduler service, Delivery worker, queue producers/consumers — an internal-message authentication layer (producer auth + integrity/replay) and a per-work-item authorization hook reusing the PDP (issue 014).
- **Actors**: Internal services as producers/consumers (each a distinct authenticated principal); the asserted owning user carried by each work item.
- **Data Classification**: Restricted (work items reference a reminder and its owning user); message envelopes carry minimal data per `FR-5.4`.

## Security Context
- **Defense Layer**: Architecture + Authentication/Authorization of internal traffic (zero trust east-west).
- **Threat(s) Addressed**: Forged/spoofed internal message (CWE-345 insufficient authenticity), replay (CWE-294), cross-user delivery via tampered owning-user assertion (CWE-639/BOLA at the worker), privilege propagation from the Scheduler's cross-user scope to delivery (`FR-5.5`). STRIDE: Spoofing, Tampering, Elevation of Privilege, Repudiation.
- **Trust Boundary**: Internal service-to-service and queue edges — each is an authenticated, authorized boundary, not an implicitly trusted internal network.
- **Zero Trust Consideration**: A peer or work item is never trusted by network position; producer authenticity and per-item user authorization are verified on every message, and any unauthenticated/unauthorizable/replayed item fails closed (reject + dead-letter).

## Standards Alignment
- **OWASP ASVS**: V13.2 (service-to-service auth), V1.4 (trust boundaries), V4.2 (object-level authz)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: AC-3 (access enforcement), IA-9 (service identification/authentication), SC-8 (transmission integrity), SI-7 (message integrity)
- **NIST SP 800-207**: zero trust applied inside the boundary; no trust by network location
- **Regulatory**: GDPR Art. 5(1)(f) integrity/confidentiality, Art. 32 (processing integrity)
- **Other**: SECURITY.md §3; ARCH Dependency Rule 8; `SEC-2.1`, `SEC-2.2`, `SEC-2.3`, `FR-5.5`

## Acceptance Criteria
1. **AC-01 (verbatim SECURITY.md §3 internal-message clause)**: Given a forged or replayed internal queue message — well-formed against schema but lacking valid producer authentication, or asserting an owning user it is not authorized for — when consumed, then it is rejected and never produces a delivery.
2. **AC-02**: Given a legitimate, producer-authenticated work item whose asserted owning user is authorized, when consumed, then it is processed exactly once (idempotent, ARCH Rule 8) and delivery proceeds subject to FR-5.5 re-verification.
3. **AC-03 (negative)**: Given a message that fails the integrity/MAC check or signature, when received, then it is rejected and dead-lettered, never processed (fail closed, `SEC-2.3`).
4. **AC-04 (negative)**: Given a replayed message (valid auth, previously processed), when consumed again, then the replay check rejects it and no duplicate delivery occurs.
5. **AC-05 (negative)**: Given a work item asserting a different owning user than the producer is entitled to enqueue for, when authorized at the consumer, then it is denied — the Scheduler's cross-user evaluation scope does not propagate as delivery authority (`FR-5.5`).
6. **AC-06**: Given a rejection (auth/integrity/replay/authorization), when it occurs, then the denial is recorded in the audit log (`SEC-8.1`) and the item is dead-lettered.

## Failure Behavior
- **On Invalid Input**: Unauthenticated/forged/replayed/unauthorizable message → reject + dead-letter; audit the denial.
- **On System Error**: Fail closed — if producer authenticity or per-item authorization cannot be determined, the item is not processed.
- **Alerting**: Dead-letter growth from auth/authorization rejections and any replay detection raise security/operational alerts (consistent with NFR-1.5 DLQ alerting).

## Test Strategy
- **Unit Tests**: Envelope MAC/signature verify; replay-nonce/timestamp check; per-item authorization against asserted owning user.
- **Integration Tests**: Forged/replayed/cross-user message is rejected and dead-lettered, no delivery (the verbatim AC); legitimate item delivered once.
- **Security Tests**: Inject forged envelopes, tampered owning-user fields, and replayed messages; assert no delivery and proper dead-lettering; confirm Scheduler scope does not grant delivery authority.
- **Compliance Tests**: Audit evidence of internal-message denials; coverage that every consumer path performs producer-auth + per-item authorization.
- **Coverage Target**: ≥ 80% branch coverage of the internal-message auth/authorization layer.

## Dependencies
- **Upstream**: 007 (Flask skeleton/shared crypto for envelope signing), 011 (KMS for MAC/signing keys), 012 (audit log for denials), 014 (PDP reused for per-item authorization), 010 (user-scoped repositories).
- **Downstream**: Scheduler (`FR-5.1`/`FR-5.2`), Delivery worker (`FR-5.4`/`FR-5.5`/`FR-6.2`), reminder-queue enqueue/consume issues, NFR-1.5 retry/dead-letter handling.
- **External**: Reminder queue/broker (`TO BE DECIDED`, DECISION 070) — the concrete producer-auth mechanism (mTLS vs. signed envelope) follows that choice; default to the most-restrictive (reject unauthenticated) behind the queue interface.

## Implementation Notes
- **Constraints**: Mechanism follows the queue/transport choice (DECISION 070) — keep behind the queue interface and default to reject-unauthenticated; do not resolve the broker here. Reuse the PDP (issue 014) for per-item authorization rather than a parallel check. This is distinct from external webhook signatures (`SEC-7.1`).
- **Anti-Patterns**: MUST NOT trust a work item by network position or queue membership; MUST NOT process an unauthenticated/forged/replayed message; MUST NOT let the Scheduler's cross-user scope imply delivery authority; MUST NOT silently drop a rejected item (dead-letter + audit instead); MUST NOT skip per-item authorization on the assumption the producer already checked.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** East-west authentication with replay protection and per-item authorization is subtle, and a gap lets a forged message deliver to the wrong user or escalate the Scheduler's scope. Favor the model with stronger reasoning about message-integrity and authorization-propagation invariants. Mandatory human security review of the envelope auth and per-item authorization before merge.
