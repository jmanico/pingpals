# Requirement: DECISION — in-app/push delivery mechanism + provider

## Metadata
- **ID**: REQ-DEC-071
- **Title**: Decide and document the in-app/push delivery mechanism and provider
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Operational
- **Decision**: **RESOLVED — standard Web Push using the application's OWN VAPID keys + RFC 8291 message-level payload encryption.** Provider-agnostic (no proprietary SDK), implemented behind a `PushSender` interface that fails closed (no push) whenever message-level protection is unavailable. Human sign-off recorded via the project owner.

## Requirement
- **Description**: **RESOLVED.** In-app/push delivery uses **standard Web Push** with the application's **own VAPID keys** for authenticated sender identity and **RFC 8291 message-level payload encryption** to the endpoint, sent directly to browser push services with **no proprietary push SDK**. The sender sits behind a `PushSender` interface that **fails closed (no push)** if message-level encryption/integrity cannot be applied. The decision is recorded with rationale against the criteria below, satisfies every listed constraint, and is signed off by a human (the project owner). The web-push adapter (issue 040) may now build against this. This issue produced NO implementation code itself and did not resolve the choice silently (`CLAUDE.md`).
- **Rationale**: MVP delivers reminders to the user via email and in-app/push (`FR-6.1`). Push routes through an intermediary outside the trust boundary, so the payload MUST use an authenticated sender and message-level encryption so the intermediary cannot read or alter it; a mechanism that cannot apply message-level protection MUST fail closed — no push (`FR-6.5`, `FR-5.6`). Endpoints must also be ownership-bound and revocable (`FR-6.5`).
- **Design**: Per `DESIGN.md`, push notification bodies render on untrusted surfaces (lock screen) and therefore MUST carry only an opaque reminder id, not contact PII (`FR-5.6`); the mechanism choice MUST accommodate this.

## Scope
- **Applies To**: Both (service worker / push subscription on the SPA; sender on the backend)
- **Components**: Web-push adapter (040), delivery worker owner-verification (035), reminder payload confidentiality (036), delivery endpoint lifecycle (037).
- **Actors**: The owning user (subscribes a push endpoint within an authenticated session); the Delivery worker (sender); human approver.
- **Data Classification**: Restricted (push endpoint is a delivery endpoint bound to one user; payload PII-handling per `FR-5.6`).

## Security Context
- **Defense Layer**: Architecture (delivery infrastructure choice).
- **Threat(s) Addressed**: Intermediary reading/altering reminder payloads (CWE-319 cleartext through a TLS-terminating push service), PII on lock screens (CWE-200), endpoint hijacking / cross-user delivery (CWE-639), unauthenticated sender spoofing. STRIDE: Information Disclosure, Spoofing, Tampering.
- **Trust Boundary**: The push intermediary terminates TLS and is outside the trust boundary; transport TLS (`SEC-5.1`) alone is insufficient (`FR-6.5`).
- **Zero Trust Consideration**: The intermediary is untrusted; the mechanism MUST apply message-level encryption/integrity (RFC 8291) and an authenticated sender (VAPID) so confidentiality/integrity do not depend on the intermediary; failure to do so fails closed (no push).

## Standards Alignment
- **OWASP ASVS**: V6.x (cryptography), V9.x (communications), V1.x (architecture)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SC-8 (transmission confidentiality/integrity), SC-13 (cryptographic protection), AC-3 (endpoint ownership)
- **NIST SP 800-207**: untrusted intermediary; per-message protection
- **Regulatory**: GDPR Art. 32 (security of processing), Art. 5(1)(c) minimization on lock-screen surfaces
- **Other**: RFC 8291 (Web Push message encryption), RFC 8030 (Web Push), VAPID; `FR-6.1`, `FR-6.5`, `FR-5.6`, `SEC-5.1`

## Evaluation Criteria (constraints any choice MUST satisfy)
1. **Authenticated sender (VAPID)** — supports an authenticated application server identity to the push service (`FR-6.5`).
2. **Message-level encryption/integrity** — supports RFC 8291 payload encryption so the intermediary cannot read or alter the reminder (`FR-6.5`, `FR-5.6`); a mechanism that cannot MUST be rejected (fail closed).
3. **Opaque-id payloads** — accommodates a body carrying only an opaque, non-guessable reminder id (no contact PII) for lock-screen/untrusted surfaces (`FR-5.6`).
4. **Endpoint ownership binding & revocation** — subscriptions registrable only in an authenticated session, bound to one user, revocable on logout/consent-withdrawal/erasure (`FR-6.5`, `FR-6.2`, `PRIV-1.6`).
5. **CSP/SRI compatibility** — service-worker/client integration compatible with the strict CSP and SRI posture (`FE-1.4`, `FE-1.8`).
6. **Cloud-portable** — not locked to a single cloud's proprietary push service in MVP (ARCH "many clouds").
7. **Delivery reliability** — supports retry/dead-letter and the ≥99.5% target on healthy channels (`NFR-1.2`, `NFR-1.5`).

## Candidate Options (evaluate, do NOT pick here)
- Standard Web Push (browser Push API + service worker) with VAPID and RFC 8291 encryption, sending directly to browser push services.
- A managed push/notification provider that supports VAPID + RFC 8291 pass-through (evaluate against cloud-portability and "intermediary cannot read payload").
- In-app delivery only for MVP (polling/SSE/WebSocket to the authenticated SPA), with web push deferred (evaluate against `FR-6.1` MVP scope).

> Each option MUST be scored against all seven criteria with rationale. This issue does not select one.

## Acceptance Criteria
1. **AC-01**: Given the candidate options, when evaluated, then each is scored against all seven criteria with documented rationale.
2. **AC-02**: **RESOLVED** — the choice (standard Web Push, own VAPID keys, RFC 8291 encryption, behind a fail-closed `PushSender` interface) is recorded in `ARCHITECTURE.md` (replacing the relevant `TO BE DECIDED`/`[ASSUMPTION]`) with rationale and explicit human sign-off (the project owner).
3. **AC-03 (negative)**: Given any candidate that cannot apply message-level encryption/integrity (RFC 8291) and VAPID, when evaluated, then it is rejected — push that cannot protect the payload fails closed and is not chosen.
4. **AC-04 (negative — no silent resolution)**: Given this issue, when worked, then no web-push adapter (040) is built and no provider is committed before human sign-off; until then the delivery path stays behind the push interface, defaulting to no-push when message-level protection is unavailable.

## Failure Behavior
- **On Invalid Input**: n/a (decision artifact).
- **On System Error**: Until resolved, dependent 040 stays blocked or behind the push interface defaulting to fail-closed (no push without message-level protection).
- **Alerting**: Flag 040 as decision-blocked on the board while this is open.

## Test Strategy
- **Unit Tests**: n/a (no code). Provide a decision matrix artifact.
- **Integration Tests**: Optional spike sending a VAPID-authenticated, RFC 8291-encrypted push to a test endpoint and confirming the intermediary cannot read the body; results feed the decision only.
- **Security Tests**: Threat-review the front-runner against intermediary read/alter and lock-screen PII exposure.
- **Compliance Tests**: Confirm opaque-id payloads satisfy `FR-5.6` minimization on untrusted surfaces.
- **Coverage Target**: n/a (decision issue).

## Dependencies
- **Upstream**: 036 (reminder payload confidentiality constraints), 037 (delivery endpoint lifecycle), 008 (CSP/SRI), decision 073 (region may constrain managed providers).
- **Downstream**: **Blocks 040** (web-push adapter); informs 035 (owner verification) and 041 (retry).
- **External**: Browser push services / chosen push provider; VAPID key management (per 072 KMS where applicable).

## Implementation Notes
- **Constraints**: Decision only — no code. Message-level encryption (RFC 8291) and VAPID are non-negotiable for push; in-app delivery is the fallback if push cannot meet them. Keep cloud-portable.
- **Anti-Patterns**: MUST NOT rely on transport TLS alone for a TLS-terminating intermediary (`FR-6.5`); MUST NOT put contact PII in a push body (`FR-5.6`); MUST NOT pick a provider implicitly via code; MUST NOT register endpoints outside an authenticated session.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Push-stack trade-off analysis over standardized web-push technologies (VAPID, RFC 8291/8030) leans on broad protocol familiarity; no code is produced. The model MUST NOT resolve the choice — it prepares the scored matrix for human sign-off, ensuring every option is graded on the message-level-encryption constraint.
