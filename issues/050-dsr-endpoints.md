# Requirement: Data subject rights endpoints and contact-DSR intake channel

## Metadata
- **ID**: REQ-PRIV-050
- **Title**: User DSR endpoints (access, portability, rectification, erasure, restriction, objection) + contact DSR intake
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Compliance

## Requirement
- **Description**: The system MUST implement data subject rights for the user: access and portability (Articles 15 and 20, via export issue 046), rectification (Article 16, with the change audited per `SEC-8.1`), erasure (Article 17, via issue 048), restriction (Article 18), and objection (Article 21). The system MUST additionally provide a documented intake channel for a data subject request originating from a contact (a non-user); at minimum the controlling user MUST be able to erase a contact's data on request, with controller-mediated erasure (the user deletes the contact) as the MVP default. The process for a direct third-party erasure request is an open decision recorded as DECISION 075 (`PRIV-1.4`, REQUIREMENTS §14).
- **Rationale**: GDPR Articles 15–21 grant the user concrete, exercisable rights; the controller must provide an effective means to exercise each. Separately, because Pingpals processes personal data of third-party data subjects (contacts) who are not users, there must be a documented channel for their requests — defaulting to controller-mediated erasure until the direct-intake process is decided. This is the data-of-record behind `PRIV-1.3` and `PRIV-1.4`.
- **Design**: Per `DESIGN.md` §6/§7, the DSR area lives in the authenticated account/privacy settings, in the gentle royal voice, presenting each right as a clear, owner-scoped action (export, fix a field, erase, restrict, object).

## Scope
- **Applies To**: Both
- **Components**: Privacy/DSR subsystem — DSR endpoints; orchestrates export (046), rectification writes, erasure (048/049), restriction and objection flags; documents the contact-DSR intake channel.
- **Actors**: Authenticated user (owner) exercising their own rights; contact (non-user) as the originator of a contact-DSR request handled by the controlling user (controller-mediated).
- **Data Classification**: Restricted/PII (the data acted upon); DSR actions themselves are audited.

## Security Context
- **Defense Layer**: Architecture (right-specific, owner-scoped endpoints) + Strict API
- **Threat(s) Addressed**: Unauthorized exercise of another user's rights (BOLA/BFLA, OWASP API1/API5:2023), unaudited rectification, processing-after-objection. STRIDE: Elevation of Privilege, Repudiation, Tampering.
- **Trust Boundary**: API service — each DSR endpoint authorizes per-request against the owning user; restriction/objection flags are enforced downstream (Scheduler/Delivery) as a fail-closed gate.
- **Zero Trust Consideration**: No DSR action trusts ambient identity; every action carries the owning user as a non-optional constraint (`SEC-2.2`) and is audited (`SEC-8.1`).

## Standards Alignment
- **OWASP ASVS**: V4.x (access control), V7.x (audit), V13.x (API)
- **OWASP AISVS**: n/a (no AI component)
- **NIST SP 800-53**: AC-3 (access enforcement), AU-2 (auditable events), SI-12 (information handling)
- **NIST SP 800-207**: per-request, owner-scoped authorization
- **Regulatory**: GDPR Arts. 12 (modalities), 15 (access), 16 (rectification), 17 (erasure), 18 (restriction), 20 (portability), 21 (objection)
- **Other**: `PRIV-1.3`, `PRIV-1.4`, `SEC-8.1`, REQUIREMENTS §14, DECISION 075

## Acceptance Criteria
1. **AC-01**: Given an authenticated user, when they invoke each DSR right (access/portability, rectification, erasure, restriction, objection), then the corresponding action executes scoped to that user (access/portability delegates to 046; erasure to 048/049).
2. **AC-02**: Given a user rectifies a contact field (Art. 16), when the change is applied, then an audit event recording the rectification of contact personal data is written (`SEC-8.1`, 012).
3. **AC-03**: Given a user sets restriction (Art. 18) or objection (Art. 21), when the Scheduler/Delivery path next runs for the affected data, then processing/delivery is suppressed (fail closed) consistent with the flag.
4. **AC-04**: Given a contact (non-user) submits a DSR via the documented intake channel, when the controlling user acts, then controller-mediated erasure of that contact is available as the MVP default, and the direct-intake decision is referenced as DECISION 075.
5. **AC-05 (negative)**: Given user A invokes any DSR endpoint targeting user B's data, when authorized, then the request returns not-found/forbidden and performs no action (`SEC-2.2`).

## Failure Behavior
- **On Invalid Input**: Reject a malformed or non-owner DSR request with HTTP 403/404/422; no action performed.
- **On System Error**: Fail closed — if a right cannot be fulfilled atomically (e.g. erasure proof gate, 049), the action aborts rather than partially applying; restriction/objection default to suppressing processing if their state is indeterminate.
- **Alerting**: Repeated failed DSR actions or cross-user DSR attempts raise a compliance/security alert.

## Test Strategy
- **Unit Tests**: Each right's handler (access→export, rectify→audited write, erase→cascade, restrict/object→flag); owner-scoping guard.
- **Integration Tests**: End-to-end exercise of each right for a user; restriction/objection suppresses a subsequent scheduler/delivery run; controller-mediated contact erasure removes the contact (maps to TEST-1.4 erasure cascade via 048).
- **Security Tests**: Cross-user DSR isolation (A cannot act on B); rectification without audit is impossible (audit-write-or-fail per `SEC-8.1`).
- **Compliance Tests**: Automated evidence that each Art. 15–21 right has a working, audited endpoint and that the contact-DSR intake is documented.
- **Coverage Target**: ≥ 80% branch coverage of the DSR endpoints module.

## Dependencies
- **Upstream**: 046 (export — access/portability), 048 (erasure cascade), 049 (proof-of-erasure), 045 (consent records — objection/withdrawal interplay), 014 (authorization), 012 (audit), 013 (rate limiting for DSR endpoints, `SEC-6.1`), 024 (contact model for rectification).
- **Downstream**: Scheduler/Delivery enforcement of restriction/objection flags; 053 (RoPA documents the DSR process and intake channel).
- **External**: None in MVP; direct third-party erasure intake process is DECISION 075 (`TO BE DECIDED`).

## Implementation Notes
- **Constraints**: DSR endpoints are rate-limited (`SEC-6.1`, 013) and audited (`SEC-8.1`, 012). Restriction/objection are enforced as fail-closed gates downstream, not merely advisory flags. The contact-DSR intake is documented (process artifact in 053) with controller-mediated erasure as the default until DECISION 075 resolves.
- **Anti-Patterns**: MUST NOT let one user exercise another user's rights; MUST NOT apply rectification without an audit event; MUST NOT continue processing after a restriction/objection is set; MUST NOT invent a direct third-party erasure process ahead of DECISION 075 — default to controller-mediated + manual DSR.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Broad orchestration across several well-specified rights, each delegating to an existing issue; suited to systematic coverage of the right set. Mandatory human privacy review of the contact-DSR intake wording and the restriction/objection enforcement points; surface DECISION 075 rather than resolving it.
