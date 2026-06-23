# Requirement: DECISION — direct third-party (contact) erasure intake, identity verification, and cross-user purge scope

## Metadata
- **ID**: REQ-DEC-075
- **Title**: Decide and document the intake, identity verification, and scope for direct third-party (contact) erasure requests
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Medium
- **Classification**: Compliance
- **Decision**: **RESOLVED FOR MVP — controller-mediated erasure** (the owning user deletes the contact via the existing erasure cascade, issue 048) **+ a documented manual DSR intake channel** for contacts. **NO automated cross-user purge is committed.** Any FUTURE identity-verified or cross-user intake remains **OPEN** and requires DPO/legal sign-off before it may be built. Human sign-off on the MVP baseline recorded via the project owner.

## Requirement
- **Description**: **RESOLVED FOR MVP.** The process for a direct erasure (and broader DSR) request from a contact (a third-party data subject who is not a user) is, for MVP, **controller-mediated erasure**: the request is routed to the owning user(s), who delete the contact through the existing hard-delete cascade (issue 048), backed by a **documented manual DSR intake channel** (`PRIV-1.4`, GDPR Art. 12). **No automated cross-user purge mechanism is committed.** Any future extension — an identity-verified intake or a defined cross-user purge — remains an **OPEN decision** (REQUIREMENTS.md §14) and MUST NOT be built without explicit DPO/legal and human sign-off (`CLAUDE.md`). This issue produces NO implementation code.
- **Rationale**: Pingpals processes personal data of third-party data subjects who hold GDPR rights exercisable through a documented channel (`PRIV-1.4`). REQUIREMENTS.md §14 records that direct third-party erasure spanning one or more users' data sets is operationally hard and that intake, identity verification, and cross-user purge scope MUST be decided and documented; it recommends starting with controller-mediated erasure plus a manual DSR process.
- **Design**: Per `DESIGN.md` §6 voice/tone, any contact-facing notice/process copy is gentle and clear; but a privacy/legal process, not a UI feature, is the deliverable.

## Scope
- **Applies To**: Both (intake may be a documented manual channel and/or an API/process touching the DSR subsystem)
- **Components**: DSR endpoints (050), erasure cascade (048), proof-of-erasure (049), consent/audit (045/012), RoPA/DPIA docs (053).
- **Actors**: Contact (non-user data subject, requester); the controlling user(s) whose data set holds the contact; DPO/legal; human approver.
- **Data Classification**: Restricted (contact PII across potentially multiple users' data sets).

## Security Context
- **Defense Layer**: Architecture / Compliance / Access control.
- **Threat(s) Addressed**: Unauthenticated or impersonated erasure request causing wrongful deletion or cross-user data exposure (CWE-285/CWE-639), enumeration of which users hold a given contact (information disclosure), denial-of-service via mass bogus DSRs. STRIDE: Spoofing, Information Disclosure, Denial of Service, Repudiation.
- **Trust Boundary**: The DSR intake boundary for a non-user actor — the hardest case, since the requester has no account and the data spans isolated per-user sets.
- **Zero Trust Consideration**: A third-party erasure request is untrusted until identity is verified; the process MUST fail closed (no purge) on unverified identity, and MUST NOT let the request enumerate or read across users' data beyond what the verified scope permits (`SEC-2.2`).

## Standards Alignment
- **OWASP ASVS**: V4.x (access control), V8.x (data protection)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: IA-x (identity verification of requester), AC-3 (access enforcement), AU-2 (audit DSR actions)
- **NIST SP 800-207**: deny-by-default for unverified requester; per-user scoping preserved
- **Regulatory**: GDPR Arts. 12 (identity verification, modalities), 15–21 (data subject rights), 17 (erasure)
- **Other**: `PRIV-1.4`, `PRIV-1.6`, `PRIV-1.16`, `SEC-2.2`, REQUIREMENTS.md §14

## Evaluation Criteria (constraints any decision MUST satisfy)
1. **Documented intake channel** — there is a documented channel for a contact to submit a DSR (`PRIV-1.4`, GDPR Art. 12).
2. **Identity verification** — a method to verify the requester is the data subject before any action, proportionate and not over-collecting (GDPR Art. 12(6)), failing closed on non-verification.
3. **Cross-user purge scope** — explicit decision on whether/how a verified request purges the contact across multiple users' data sets, preserving per-user isolation and avoiding enumeration leakage (`SEC-2.2`).
4. **Controller-mediated baseline** — MVP default of user-deletes-the-contact (`PRIV-1.4`) is documented as the minimum, with any extension clearly scoped.
5. **Cascade & proof** — any executed erasure follows the hard-delete cascade and leaves a surviving PII-free proof-of-erasure record (`PRIV-1.6`, `PRIV-1.16`).
6. **Audit & rate-limiting** — DSR actions are audited (`SEC-8.1`) and the intake is rate-limited against abuse (`SEC-6.1`).
7. **Legal sign-off** — reviewed by a qualified data protection advisor before adoption (§14).

## Candidate Options (evaluate, do NOT pick one prematurely)
- **Controller-mediated only (MVP recommendation)**: contact requests are routed to the owning user(s) who delete the contact; the platform provides no direct cross-user purge.
- **Manual DSR with verified identity**: a documented manual process where the controller verifies identity and erases across affected users' data sets.
- **Self-service direct intake**: an automated intake with strong identity proofing and a defined cross-user purge (highest complexity/risk; evaluate against enumeration and DoS).

> Each option MUST be assessed against all seven criteria with rationale and legal input. The MVP default is controller-mediated; any extension requires explicit human sign-off — this issue does not silently build a cross-user purge.

## Acceptance Criteria
1. **AC-01**: Given the candidate options, when evaluated (with DPO/legal input), then each is assessed against all seven criteria with documented rationale.
2. **AC-02**: **RESOLVED FOR MVP** — the controller-mediated baseline plus a documented manual DSR intake channel is recorded in REQUIREMENTS.md §14 / privacy docs (053) with rationale and explicit human sign-off (the project owner). The identity-verification method and any cross-user purge scope for a future direct intake remain **OPEN** pending DPO/legal sign-off.
3. **AC-03 (negative)**: Given an unverified or impersonated third-party erasure request, when received under the documented process, then it fails closed (no purge) and discloses no cross-user information; the request is audited and rate-limited.
4. **AC-04 (negative — no silent resolution)**: Given this issue, when worked, then no cross-user purge mechanism is built and only the controller-mediated baseline is assumed until a human signs off on any extension.

## Failure Behavior
- **On Invalid Input**: An unverified requester is denied; the process does not reveal which users hold the contact.
- **On System Error**: Until resolved, only the controller-mediated baseline (user deletes contact via 048) is available; no direct third-party cross-user purge path exists.
- **Alerting**: A spike in third-party DSR intake or repeated verification failures raises an abuse/operational alert (`SEC-6.1`).

## Test Strategy
- **Unit Tests**: n/a (no code in this issue). If the chosen process later adds endpoints, those are covered under 050 with identity-verification and fail-closed tests.
- **Integration Tests**: n/a for the decision; the controller-mediated path is exercised by the erasure-cascade tests (067/048).
- **Security Tests**: Threat-review the recommended process against impersonation, enumeration, and DSR-flood abuse.
- **Compliance Tests**: Confirm the documented process satisfies GDPR Art. 12 modalities and that executed erasures leave proof-of-action (`PRIV-1.16`).
- **Coverage Target**: n/a (decision issue).

## Dependencies
- **Upstream**: 048 (erasure cascade — the executor for any decided process), 050 (DSR endpoints), 049 (proof-of-erasure), 053 (RoPA/DPIA/LIA), decision 073 (jurisdiction shapes obligations); requires DPO/legal review.
- **Downstream**: Any future direct third-party intake implementation depends on this decision; informs 050 and 053.
- **External**: DPO/legal advisory; identity-verification approach.

## Implementation Notes
- **Constraints**: Decision only — no code. MVP stays controller-mediated per §14 recommendation; any extension to a cross-user purge requires explicit human sign-off and legal review. Preserve per-user isolation (`SEC-2.2`) throughout.
- **Anti-Patterns**: MUST NOT build an unauthenticated/enumerable third-party erasure endpoint; MUST NOT over-collect identity data for verification (GDPR Art. 12(6)); MUST NOT silently implement a cross-user purge; MUST NOT skip the proof-of-erasure record for any executed deletion.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Designing a privacy/DSR process for a non-user data subject spanning isolated per-user data sets is a high-stakes reasoning problem (impersonation, enumeration, cross-user scope, GDPR Art. 12 proportionality) where careful adversarial and regulatory reasoning matters even though no code is produced. The model MUST NOT resolve the choice — it prepares the assessment for human DPO/legal sign-off, defaulting to the controller-mediated baseline.
