# Requirement: OIDC ID-token validation and immutable-subject account binding

## Metadata
- **ID**: REQ-AUTH-018
- **Title**: Full ID-token validation before session establishment; account keyed on immutable `sub`, never on mutable email
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Critical
- **Classification**: Security

## Requirement
- **Description**: On the OIDC callback (the Google SSO login path), the system MUST fully validate the returned ID token BEFORE any session is established. The token signature MUST be verified against the provider's published JWKS, and the `iss`, `aud` (which MUST equal the registered client id), `exp`, and `iat` claims MUST be checked. A single-use `nonce` generated per authorization request (issue 017), bound to the initiating user agent, MUST be matched against the returned token's `nonce`. The local user account MUST be bound to the IdP's immutable subject identifier (`sub`), scoped to the validated issuer (`iss`), and MUST NOT be keyed on, linked by, or merged on any mutable attribute such as email address or display name. Email MUST be treated as a non-authoritative display attribute only, and any email consumed MUST carry `email_verified` true. Identity resolution MUST fail closed: if `sub` is absent, or `email_verified` is false where an email is used, the login MUST be denied. Any validation failure MUST fail closed — no session is established and no session cookie is issued.
- **Rationale**: An unvalidated or replayed ID token lets an attacker forge an authenticated identity; keying accounts on email (a mutable, recyclable attribute) lets email change/recycling silently merge, hijack, or lock out accounts. Binding to the immutable `(iss, sub)` pair and demanding `email_verified` closes both. This is the callback-validation half; initiation/`nonce` issuance is issue 017 and session promotion is issue 019.
- **Design**: Backend AuthN-subsystem concern. On failure the UI surfaces a gentle, non-blaming error per `DESIGN.md` §6 without leaking which check failed.

## Scope
- **Applies To**: Both
- **Components**: AuthN/Session subsystem (ID-token validator, JWKS client, account-resolution service); consumes the transaction-state record (issue 017).
- **Actors**: Anonymous user completing Google SSO login; the external IdP as token issuer.
- **Data Classification**: Confidential (ID token, session material); email is non-authoritative display data.

## Security Context
- **Defense Layer**: Input Validation (token + claim validation) + Architecture (immutable-subject identity model)
- **Threat(s) Addressed**: ID-token forgery/substitution (CWE-347 improper signature verification), token replay (missing/`nonce` reuse), audience confusion / token reuse across clients, account takeover and silent merge via email recycling (CWE-287, CWE-639). STRIDE: Spoofing, Tampering, Elevation of Privilege.
- **Trust Boundary**: Trust boundary with the external IdP — the ID token is untrusted until every claim and the signature validate.
- **Zero Trust Consideration**: The token is treated as untrusted input regardless of transport security; signature, issuer, audience, expiry, and `nonce` are independently verified server-side before any trust (a session) is granted.

## Standards Alignment
- **OWASP ASVS**: V51/V52 (OIDC ID-token validation, `nonce`), V3 (session establishment)
- **OWASP AISVS**: n/a (no AI component)
- **NIST SP 800-53**: IA-2, IA-5, IA-8 (authenticator/identity management)
- **NIST SP 800-207**: independent verification of asserted identity before granting access
- **Regulatory**: GDPR Art. 5(1)(f)/Art. 32 — preventing unauthorized access to personal data via account confusion
- **Other**: OIDC Core (ID-token validation, `nonce`), RFC 9068, RFC 7519 (JWT); `INT-1.8`, `INT-1.9`, SECURITY §2

## Acceptance Criteria
1. **AC-01**: Given a callback ID token, when validated, then the signature verifies against the provider JWKS and `iss`, `aud` (= registered client id), `exp`, `iat`, and a single-use `nonce` bound to the initiating user agent all check; only then may a session be established.
2. **AC-02 (negative)**: Given an ID token with a wrong `aud`, an invalid or absent signature, an expired `exp`, or a missing or mismatched `nonce`, when validated, then it is rejected and no session cookie is issued. *(verbatim `INT-1.8`.)*
3. **AC-03**: Given a successful login, when the account is resolved, then it is bound to the immutable `sub` scoped to the validated `iss`; email is stored only as a non-authoritative display attribute and only when `email_verified` is true.
4. **AC-04 (negative)**: Given the IdP email for an address is changed, deleted, or recycled, when a login occurs, then it does not grant access to, lock out, or silently merge with another user's account; given a token whose `sub` does not match the bound account, then it is rejected. *(verbatim `INT-1.9`.)*
5. **AC-05 (negative)**: Given a token with absent `sub`, or `email_verified` false where an email is used, when identity resolution runs, then the login is denied (fail closed).

## Failure Behavior
- **On Invalid Input**: Reject with an authentication failure (no session, no cookie), write an authentication-failure audit event (`SEC-8.1`) with a correlation id, and return a generic error that does not reveal which claim failed.
- **On System Error**: Fail closed — if JWKS cannot be fetched/verified or the validator errors, deny the login; never downgrade to an unvalidated path.
- **Alerting**: Alert on a spike in signature/`aud`/`nonce` failures (possible token-forgery or replay campaign) and on JWKS fetch failures.

## Test Strategy
- **Unit Tests**: Claim checks (`iss`, `aud`, `exp`, `iat`, `nonce`); signature verification against test JWKS incl. key rotation; `email_verified` gating; `sub`-based account resolution; rejection of absent `sub` and of `sub` mismatch.
- **Integration Tests**: End-to-end callback with valid token → session; tampered/expired/wrong-`aud`/missing-`nonce` tokens → no session; email-recycle scenario asserts no merge/lockout/grant.
- **Security Tests**: Forged-signature and `alg=none` corpus; cross-client `aud` reuse; `nonce` replay; account-confusion via email mutation (maps to TEST-1.3 token/identity cases).
- **Compliance Tests**: Assert authentication-failure audit entries are written and attributable.
- **Coverage Target**: ≥ 80% branch coverage of the validator and account-resolution modules.

## Dependencies
- **Upstream**: 017 (initiation issues the `nonce`/expected `iss` and stores the single-use transaction record this consumes).
- **Downstream**: 019 (session is promoted only after this validation passes), 023 (account linking reuses identity resolution but is account-mutating and requires re-auth).
- **External**: Google OIDC JWKS endpoint; a vetted JWT/JOSE library (`SEC-9.x`).

## Implementation Notes
- **Constraints**: Verify signature before reading claims; enforce a small clock-skew tolerance on `exp`/`iat`; cache JWKS with bounded TTL and handle key rotation; the `nonce` is single-use and bound to the initiating UA (from issue 017's transaction record). Account key is `(iss, sub)`; email is a separate, non-authoritative column.
- **Anti-Patterns**: MUST NOT accept `alg=none` or skip signature verification; MUST NOT key, link, or merge accounts on email/display name; MUST NOT establish any session or set a cookie before all checks pass; MUST NOT consume an email with `email_verified` false; MUST NOT leak the failing check to the client.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** ID-token validation and immutable-subject binding are dense, high-stakes correctness problems where a single skipped claim is account takeover; use the model with the strongest adversarial reasoning on JWT/OIDC pitfalls. Mandatory human security review before merge.
