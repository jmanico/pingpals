# Requirement: WebAuthn credential registration (server-verified, session-bound, fail-closed)

## Metadata
- **ID**: REQ-AUTH-020
- **Title**: WebAuthn/passkey registration ceremony within an authenticated session, bound to the immutable user id
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Security

## Requirement
- **Description**: The system MUST support WebAuthn/passkey credential registration with server-side verification that fails closed (reject, never downgrade) on any failed check. Registration MUST occur within an already-authenticated session and MUST bind the resulting credential to the immutable user id. The registration challenge MUST be a fresh, server-generated, single-use value bound to the in-flight ceremony and consumed on use. The attestation/registration ceremony's relying-party (RP) ID and `origin` MUST exactly match the registered values. Any failed check — stale or reused challenge, mismatched RP ID or `origin`, malformed attestation — MUST reject the registration and create no credential.
- **Rationale**: WebAuthn is the phishing-resistant factor backing MFA (`SEC-1.1`). Registering only inside an authenticated session and binding to the immutable user id prevents an attacker from attaching their authenticator to a victim's account. Exact RP-ID/`origin` matching and a fresh single-use challenge defeat cross-origin and replay registration attacks. This is the **registration** half; assertion/MFA verification is issue 021.
- **Design**: Backend ceremony plus a thin client `navigator.credentials.create()` call; the "add a passkey" affordance follows `DESIGN.md` §7 (Royal Purple primary action, Gilt focus ring). No PII in the challenge.

## Scope
- **Applies To**: Both
- **Components**: AuthN/Session subsystem (WebAuthn registration verifier, challenge store, credential repository); React SPA (registration ceremony trigger only — no security decision client-side).
- **Actors**: Authenticated user registering a passkey for their own account.
- **Data Classification**: Confidential (credential public key, credential id, challenge); bound to a Restricted user account.

## Security Context
- **Defense Layer**: Architecture (phishing-resistant factor) + Input Validation (ceremony verification)
- **Threat(s) Addressed**: Credential injection/attachment to another account (CWE-287/CWE-639), registration replay via reused challenge, cross-origin/phishing registration (RP-ID/`origin` mismatch, CWE-346). STRIDE: Spoofing, Tampering, Elevation of Privilege.
- **Trust Boundary**: Client-server edge — the attestation response is untrusted; the server verifies the ceremony and is the sole authority on whether a credential is created.
- **Zero Trust Consideration**: The attestation object is treated as untrusted input; the server independently verifies challenge freshness/consumption, RP ID, and `origin` and binds to the session's immutable user id before storing anything.

## Standards Alignment
- **OWASP ASVS**: V3/V51 (authenticator registration, challenge handling)
- **OWASP AISVS**: n/a (no AI component)
- **NIST SP 800-53**: IA-2, IA-5 (authenticator management), IA-8
- **NIST SP 800-207**: independent server-side verification of an asserted authenticator
- **Regulatory**: GDPR Art. 32 — strong authentication protecting access to personal data
- **Other**: W3C WebAuthn Level 2/3, FIDO2; `SEC-1.1`, SECURITY §2, ARCH Dependency Rule 3

## Acceptance Criteria
1. **AC-01**: Given an authenticated user, when registration begins, then a fresh, server-generated, single-use challenge bound to the in-flight ceremony is issued and consumed on use.
2. **AC-02**: Given a completed registration ceremony, when the server verifies it, then the attestation's RP ID and `origin` exactly match the registered values and the new credential is bound to the session user's immutable user id.
3. **AC-03 (negative)**: Given a registration attempt initiated outside an authenticated session, when processed, then it is rejected and no credential is created.
4. **AC-04 (negative)**: Given a registration with a stale or reused challenge, or a mismatched RP ID or `origin`, when verified, then it is rejected (fail closed) and no credential is created.

## Failure Behavior
- **On Invalid Input**: Reject with HTTP 400/403, write an authentication-event audit entry (`SEC-8.1`) with a correlation id, store no credential, and return a generic error.
- **On System Error**: Fail closed — any verification error or challenge-store failure rejects the registration; never downgrade to an unverified credential.
- **Alerting**: Alert on repeated registration failures for an account (possible credential-injection attempt) and on challenge-store unavailability.

## Test Strategy
- **Unit Tests**: Challenge generation (fresh, single-use, ceremony-bound) and consumption; RP-ID/`origin` exact-match checks; binding to the immutable user id; rejection of registration outside an authenticated session.
- **Integration Tests**: Authenticated registration round-trip stores a usable credential; out-of-session attempt rejected; stale/reused-challenge and RP-ID/`origin`-mismatch attempts rejected.
- **Security Tests**: Replay a consumed challenge; submit a mismatched `origin`/RP ID; attempt to bind a credential to a different user id.
- **Compliance Tests**: Assert registration events are audit-logged and attributable.
- **Coverage Target**: ≥ 80% branch coverage of the registration verifier and challenge store.

## Dependencies
- **Upstream**: 019 (must run inside an authenticated, server-managed session).
- **Downstream**: 021 (assertion/MFA verifies credentials registered here).
- **External**: A vetted WebAuthn/FIDO2 server library (`SEC-9.x`); credential store behind the persistence layer.

## Implementation Notes
- **Constraints**: Challenge from a CSPRNG, single-use, bound to the ceremony, consumed on first use; RP ID and `origin` compared by exact match; registration gated on an authenticated session and bound to the immutable user id.
- **Anti-Patterns**: MUST NOT permit registration on an anonymous/pre-auth session; MUST NOT reuse a challenge; MUST NOT accept a mismatched RP ID/`origin`; MUST NOT make any registration decision client-side (ARCH Rule 3); MUST NOT downgrade a failed ceremony to a weaker factor.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** WebAuthn ceremony verification has many easy-to-miss server-side checks whose omission breaks phishing resistance; use the model with the strongest adversarial reasoning on the WebAuthn spec. Mandatory human security review before merge.
