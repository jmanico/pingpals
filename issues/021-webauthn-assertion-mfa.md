# Requirement: WebAuthn assertion verification as phishing-resistant MFA (UV + counter, fail closed)

## Metadata
- **ID**: REQ-AUTH-021
- **Title**: WebAuthn/passkey assertion verification with user-verification and monotonic signature-counter enforcement
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Security

## Requirement
- **Description**: The system MUST verify every WebAuthn assertion server-side and MUST fail closed (reject, never downgrade) on any failed check. The assertion's relying-party (RP) ID and `origin` MUST exactly match the registered values. The challenge MUST be a fresh, server-generated, single-use value bound to the in-flight ceremony and consumed on use. User verification (UV) MUST be asserted for the factor to count as phishing-resistant MFA. The signature counter MUST be monotonic; a non-increasing counter MUST be rejected as a cloned or replayed authenticator. The assertion MUST resolve to exactly one registered credential for the owning user, otherwise it MUST be denied. A successful MFA step-up MUST trigger issuance of a fresh session identifier (issue 019).
- **Rationale**: The assertion is where phishing resistance is actually delivered: exact RP-ID/`origin` matching stops relay/phishing, a single-use challenge stops replay, UV ensures a genuine MFA factor (not mere possession), and the monotonic counter detects cloned authenticators. Resolving to exactly one owned credential enforces per-user binding. This is the **assertion** half; registration is issue 020.
- **Design**: Backend ceremony plus a thin client `navigator.credentials.get()`; the login/step-up affordance follows `DESIGN.md` §7 and the gentle error tone of §6 on failure. No PII in the challenge.

## Scope
- **Applies To**: Both
- **Components**: AuthN/Session subsystem (assertion verifier, challenge store, credential lookup); React SPA (assertion ceremony trigger only — no security decision client-side); issue 019 (session rotation on step-up).
- **Actors**: User authenticating or performing MFA step-up with a passkey they own.
- **Data Classification**: Confidential (assertion, challenge, signature counter); bound to a Restricted user account.

## Security Context
- **Defense Layer**: Architecture (phishing-resistant MFA) + Input Validation (assertion verification)
- **Threat(s) Addressed**: Authentication replay (reused challenge), phishing/relay via origin mismatch (CWE-346, CWE-290), cloned/replayed authenticator (non-incrementing counter), cross-user credential use (CWE-639), MFA downgrade. STRIDE: Spoofing, Tampering, Elevation of Privilege.
- **Trust Boundary**: Client-server edge — the assertion is untrusted; the server alone decides whether authentication succeeds.
- **Zero Trust Consideration**: The assertion is treated as untrusted input; the server independently verifies RP ID, `origin`, single-use challenge, UV flag, counter monotonicity, and exactly-one-owned-credential before granting any session.

## Standards Alignment
- **OWASP ASVS**: V3/V51 (authenticator assertion verification, UV, replay)
- **OWASP AISVS**: n/a (no AI component)
- **NIST SP 800-53**: IA-2(1)/(2) (MFA), IA-5, IA-8
- **NIST SP 800-207**: independent verification of the asserted authenticator per access
- **Regulatory**: GDPR Art. 32 — strong MFA protecting access to personal data
- **Other**: W3C WebAuthn Level 2/3, FIDO2; `SEC-1.1`, SECURITY §2, ARCH Dependency Rule 3

## Acceptance Criteria
1. **AC-01**: Given a valid assertion from a registered credential, when verified, then RP ID and `origin` exactly match, the single-use challenge is consumed, UV is asserted, the signature counter strictly increases, the assertion resolves to exactly one credential owned by the user, and only then is authentication/step-up granted.
2. **AC-02**: Given a successful MFA step-up, when it completes, then a fresh session identifier is issued and the prior session is invalidated (via issue 019).
3. **AC-03 (negative)**: Given an assertion with a mismatched `origin`/RP ID, a stale or reused challenge, an absent UV flag, or a non-incrementing signature counter, when verified, then it is rejected and creates no session. *(verbatim SECURITY §2: an assertion with a mismatched origin/RP ID, a stale or reused challenge, an absent UV flag, or a non-incrementing signature counter is rejected and creates no session.)*
4. **AC-04 (negative)**: Given an assertion that does not resolve to exactly one registered credential for the owning user, when verified, then it is denied.

## Failure Behavior
- **On Invalid Input**: Reject with an authentication failure, write an authentication-event/denial audit entry (`SEC-8.1`) with a correlation id, grant no session, and return a generic error revealing no specific check.
- **On System Error**: Fail closed — any verification error, challenge-store failure, or ambiguous credential resolution denies authentication; never downgrade or skip the factor.
- **Alerting**: Alert on non-incrementing-counter rejections (possible cloned authenticator) and on repeated assertion failures for an account.

## Test Strategy
- **Unit Tests**: RP-ID/`origin` exact match; single-use challenge consumption; UV-flag enforcement; counter monotonicity (reject equal/lower); exactly-one-owned-credential resolution.
- **Integration Tests**: Successful assertion grants a session and (on step-up) rotates the session id; each failure class (origin/RP-ID mismatch, stale/reused challenge, absent UV, non-incrementing counter, cross-user credential) rejected with no session.
- **Security Tests**: Replay a consumed assertion; relay from a wrong origin; submit an authenticator with a reset/lower counter; attempt to use another user's credential.
- **Compliance Tests**: Assert authentication and denial events are audit-logged and attributable; assert step-up rotation event recorded.
- **Coverage Target**: ≥ 80% branch coverage of the assertion verifier.

## Dependencies
- **Upstream**: 020 (credentials must be registered first), 019 (session rotation on successful step-up).
- **Downstream**: 022/023 (account-mutating flows requiring fresh re-auth may invoke MFA step-up).
- **External**: A vetted WebAuthn/FIDO2 server library (`SEC-9.x`); credential store behind the persistence layer.

## Implementation Notes
- **Constraints**: Challenge from a CSPRNG, single-use, ceremony-bound, consumed on use; RP ID/`origin` compared by exact match; persist and compare the signature counter per credential (reject non-increasing); require the UV flag for the factor to count as MFA; resolve to exactly one owned credential.
- **Anti-Patterns**: MUST NOT accept an absent UV flag as MFA; MUST NOT accept an equal or lower signature counter; MUST NOT reuse a challenge; MUST NOT accept a mismatched RP ID/`origin`; MUST NOT make the decision client-side (ARCH Rule 3); MUST NOT keep the same session id after step-up.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Assertion verification packs several subtle, security-critical checks (UV, counter, single-use challenge) whose omission silently breaks MFA; use the model with the strongest adversarial reasoning on the WebAuthn spec. Mandatory human security review before merge.
