# Requirement: Delivery-endpoint registration, ownership binding, and lifecycle (fail closed)

## Metadata
- **ID**: REQ-DEL-037
- **Title**: Proof-of-control registration, single-owner binding, pre-delivery ownership check, and revoke/purge on logout/withdrawal/erasure
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Security

## Requirement
- **Description**: Every delivery endpoint (email address, web-push subscription, and any later-phase channel address) MUST be registered only within an authenticated session, verified by **proof of control**, and bound to **exactly one** owning user before it may receive any reminder. Registering, replacing, or removing an endpoint MUST require the authenticated owning user and MUST NOT be possible by any unauthenticated or cross-user path. Before each delivery the worker MUST confirm the target endpoint is owned by the reminder's user and MUST **fail closed** (skip that channel) if ownership cannot be verified. Endpoints MUST be **revoked and purged** on logout, on withdrawal of that channel's consent (`FR-6.2`), and on account erasure (`PRIV-1.6`). Where push delivery routes through an intermediary outside the trust boundary, the payload MUST use an authenticated sender (e.g. VAPID) and message-level encryption/integrity protection (web push: RFC 8291/RFC 8030) — transport TLS alone is insufficient — and a mechanism that cannot apply message-level protection MUST fail closed (no push delivery).
- **Rationale**: An endpoint is the address PII is sent to; if it could be registered without proof of control or bound to the wrong user, an attacker could redirect another user's reminders to their own inbox/subscription (`SEC-2.2`). Proof of control + single-owner binding + pre-send ownership re-check is the endpoint-side complement to the worker re-verification in issue 035. Revoke-on-withdrawal/erasure enforces GDPR storage-limitation and consent fail-closed.
- **Design**: Per `DESIGN.md` §6, endpoint verification (e.g. confirm-your-email / subscribe-in-app) is a calm, explicit step; a pending-unverified endpoint never receives reminders and is shown as "awaiting confirmation."

## Scope
- **Applies To**: Both (API endpoint-management routes + Web App registration UI / push subscription)
- **Components**: Endpoint registry (per-user, 010); proof-of-control verification flow; delivery worker pre-send check (035); consent store (034); erasure cascade (issue 052/PRIV-1.6); VAPID/RFC 8291 push path (040); audit log (012).
- **Actors**: Authenticated user (owner). Push intermediary as an untrusted relay.
- **Data Classification**: Restricted (email address, push subscription endpoint + keys, owning-user binding).

## Security Context
- **Defense Layer**: Architecture (ownership binding) + Authentication of endpoint control
- **Threat(s) Addressed**: Endpoint hijack / reminder redirection (CWE-639, OWASP API1:2023), unverified-address abuse (CWE-345 insufficient verification of data authenticity), intermediary read/tamper of push (CWE-300). STRIDE: Spoofing, Tampering, Information Disclosure, Repudiation.
- **Trust Boundary**: The authenticated session is the only path to mutate endpoints; the push intermediary sits outside the trust boundary and is assumed hostile to payload confidentiality/integrity.
- **Zero Trust Consideration**: An endpoint is never trusted on assertion — control is proven at registration, ownership is re-checked before every send, and a TLS-terminating intermediary is given only an authenticated, message-level-encrypted payload it cannot read or alter.

## Standards Alignment
- **OWASP ASVS**: V13/V11 (access control), V2 (authentication), V8 (data protection)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: IA-3/IA-9 (device/service identification), AC-3 (access enforcement), SC-8 (transmission confidentiality), SI-12 (information retention/disposal)
- **NIST SP 800-207**: per-action authorization; untrusted-intermediary assumption
- **Regulatory**: GDPR Art. 5(1)(e) storage limitation, Art. 7(3) withdrawal, Art. 17 erasure
- **Other**: `FR-6.5`, `FR-6.2`, `PRIV-1.6`, RFC 8291, RFC 8030, VAPID (RFC 8292)

## Acceptance Criteria
1. **AC-01**: Given an authenticated user, when they register an endpoint and complete proof of control, then it is bound to exactly that user and becomes eligible to receive reminders.
2. **AC-02 (verbatim `FR-6.5`)**: Given a subscription or address registered without ownership verification, or bound to a different user, when reminders are evaluated, then it receives no reminders.
3. **AC-03 (verbatim `FR-6.5`)**: Given a delivery whose endpoint ownership cannot be verified, when the worker runs, then it is skipped, not sent.
4. **AC-04 (verbatim `FR-6.5`)**: Given a reminder pushed through an intermediary, when in transit, then it cannot be read or modified.
5. **AC-05 (verbatim `FR-6.5`)**: Given an endpoint revoked on logout, consent withdrawal, or erasure, when reminders are evaluated thereafter, then it receives no further messages.
6. **AC-06 (negative)**: Given an unauthenticated or cross-user request to register/replace/remove an endpoint, when submitted, then it is rejected and no endpoint state changes.
7. **AC-07 (negative)**: Given a push path that cannot apply message-level (RFC 8291) protection, when delivery is attempted, then push fails closed (no delivery) rather than sending a TLS-only payload.

## Failure Behavior
- **On Invalid Input**: Registration without proof of control, or for another user, is rejected; no binding is created.
- **On System Error**: Fail closed — unverifiable ownership skips the channel; an intermediary path that cannot be message-level-protected sends nothing.
- **Alerting**: Repeated cross-user endpoint-mutation attempts or a spike in ownership-unverifiable skips MUST raise a security alert.

## Test Strategy
- **Unit Tests**: Proof-of-control state machine; single-owner binding; pre-send ownership check; revoke-and-purge triggers (logout/withdrawal/erasure).
- **Integration Tests**: Register+verify endpoint, deliver; cross-user/unverified endpoint receives nothing; revoke on each trigger stops delivery; intermediary path uses VAPID + RFC 8291.
- **Security Tests**: Attempt to register a foreign user's address; replay a registration; capture push traffic and assert it is unreadable/untamperable (maps to TEST-1.3/TEST-1.4).
- **Compliance Tests**: Erasure/withdrawal purges the endpoint and writes an audit entry (`PRIV-1.6`, `SEC-8.1`).
- **Coverage Target**: ≥ 80% branch coverage of the endpoint-registry/verification modules.

## Dependencies
- **Upstream**: 010 (per-user persistence), 011 (encryption of subscription keys at rest), 012 (audit), 014 (authz), 019 (session — logout trigger), 034 (consent withdrawal trigger).
- **Downstream**: 035 (worker pre-send check consumes the registry), 040 (web-push VAPID/RFC 8291 path), 038 (email endpoint), 052/erasure cascade.
- **External**: Standard Web Push + VAPID keypair (DECISION 071, resolved: standard Web Push with own VAPID keys + RFC 8291); transactional email provider (038).

## Implementation Notes
- **Constraints**: Endpoint records are per-user and encrypted at rest (011); push subscription keys are Restricted secrets and never logged (`SEC-8.2`). Push provider/mechanism is resolved to standard Web Push with the app's own VAPID keys + RFC 8291 (DECISION 071) — keep behind the adapter interface and default to "no push" when message-level protection cannot be guaranteed.
- **Anti-Patterns**: MUST NOT accept an endpoint without proof of control; MUST NOT allow an unauthenticated/cross-user mutation path; MUST NOT bind one endpoint to multiple users; MUST NOT rely on transport TLS for confidentiality past a terminating intermediary; MUST NOT retain a revoked/erased endpoint.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Ownership binding and proof-of-control are high-leverage security boundaries where a redirection bug is directly exploitable; favor strong adversarial reasoning. Mandatory human security review; keep the pre-send check in lockstep with issue 035.
