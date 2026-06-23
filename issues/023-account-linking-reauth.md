# Requirement: Account/identity linking requires fresh re-auth and same-session callback binding

## Metadata
- **ID**: REQ-AUTH-023
- **Title**: Linking a provider identity or integration token requires fresh re-authentication and binds only to the initiating session
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Security

## Requirement
- **Description**: Linking a provider identity or integration token to an account is an account-mutating action and MUST require a fresh authentication step (re-auth) by the session user before the link is committed. The resulting provider identity or token MUST be bound only to the user of the same session that initiated the authorization request, relying on the per-session `state`/PKCE binding (issues 017/022). A callback whose session or re-auth binding does not match MUST fail closed and link no identity or token.
- **Rationale**: Without fresh re-auth, an attacker who momentarily controls a session (or via CSRF/session-riding) could attach their own provider identity or token to a victim's account, or attach a victim's identity to their own account (a login-CSRF / account-takeover class). Requiring a fresh re-auth and binding the callback to the exact initiating session closes both the confused-deputy and replay-into-another-session attacks.
- **Design**: Backend AuthN/integration concern; the "link account / connect provider" flow surfaces a re-auth prompt (passkey/MFA step-up via issue 021) styled per `DESIGN.md` §7, with the gentle failure tone of §6 when binding fails.

## Scope
- **Applies To**: Both
- **Components**: AuthN/Session subsystem (re-auth/step-up gate), OAuth provider adapter (issue 022) and initiation (issue 017) for the per-session `state`/PKCE binding, identity-resolution service (issue 018), account-link/token-link repository.
- **Actors**: Authenticated user linking a new provider identity or integration token to their own account.
- **Data Classification**: Restricted (linked provider identity, integration tokens); Confidential (session/transaction binding).

## Security Context
- **Defense Layer**: Architecture (account-mutation gating) + Authorization (same-session binding)
- **Threat(s) Addressed**: Account-link CSRF / login-CSRF (CWE-352), session riding / confused deputy linking (CWE-441), callback replay into a different session, unauthorized identity/token attachment (CWE-639, account takeover). STRIDE: Spoofing, Tampering, Elevation of Privilege.
- **Trust Boundary**: Client-server edge plus the trust boundary with the external provider; the callback is untrusted until its session and re-auth bindings are verified.
- **Zero Trust Consideration**: The callback is treated as untrusted; the link is committed only after independent verification of a fresh re-auth and that the callback's session matches the exact session that initiated the authorization request — prior authentication alone is insufficient.

## Standards Alignment
- **OWASP ASVS**: V3 (re-authentication for sensitive operations), V51/V52 (OAuth binding, `state`)
- **OWASP AISVS**: n/a (no AI component)
- **NIST SP 800-53**: IA-11 (re-authentication), AC-3, AC-4
- **NIST SP 800-207**: re-verify trust for an account-mutating action; no implicit trust from prior auth or network position
- **Regulatory**: GDPR Art. 32 — preventing unauthorized linking/access to personal data
- **Other**: RFC 9700 (OAuth security BCP), OWASP CSRF Cheat Sheet; `INT-1.10`, SECURITY §2

## Acceptance Criteria
1. **AC-01**: Given an authenticated session user initiates a provider-identity or integration-token link, when the link is about to be committed, then a fresh re-authentication step by that session user is required before the commit.
2. **AC-02**: Given a successful re-auth and a callback whose session matches the one that initiated the authorization request, when processed, then the provider identity or token is bound to that same session's user.
3. **AC-03 (negative)**: Given a callback completed in, or replayed into, a session different from the one that initiated the flow, or one lacking the fresh re-auth, when processed, then it is rejected and links no identity or token. *(verbatim `INT-1.10`: a callback completed in, or replayed into, a session different from the one that initiated the flow, or one lacking the fresh re-auth, is rejected and links no identity or token.)*
4. **AC-04 (negative)**: Given a cross-site or forged request attempting to commit a link without the per-session `state`/PKCE binding, when evaluated, then it fails closed and no link is created.

## Failure Behavior
- **On Invalid Input**: Reject with HTTP 403, write an authorization-denial audit entry (`SEC-8.1`) with a correlation id, commit no link, and disclose no internal detail.
- **On System Error**: Fail closed — if re-auth state, session binding, or the `state`/PKCE match is indeterminate, deny the link rather than committing.
- **Alerting**: Alert on link attempts failing the session/re-auth binding (possible link-CSRF / takeover attempt).

## Test Strategy
- **Unit Tests**: Re-auth gate enforcement; same-session binding check against the initiating transaction record; rejection when re-auth absent or session mismatched.
- **Integration Tests**: Successful link with fresh re-auth + matching session; callback replayed into a different session rejected; link attempt without re-auth rejected; cross-site link commit rejected (CSRF defense, SECURITY §3).
- **Security Tests**: Login/link-CSRF corpus; callback replay into another session; attempt to attach an attacker identity to a victim account and vice versa.
- **Compliance Tests**: Assert link and denial events are audit-logged and attributable (`SEC-8.1`).
- **Coverage Target**: ≥ 80% branch coverage of the link-commit and binding-verification logic.

## Dependencies
- **Upstream**: 017 (per-session `state`/PKCE transaction binding), 022 (OAuth adapter producing the identity/token), 018 (identity resolution), 021 (re-auth / MFA step-up), 019 (session that must match), CSRF protection on mutating routes (SECURITY §3).
- **Downstream**: Integration adapters whose tokens are linked (Google People, email, later providers); consent records when linking broadens authority (`PRIV-1.2`).
- **External**: The external OAuth/OIDC provider.

## Implementation Notes
- **Constraints**: Re-auth uses the existing passkey/MFA step-up (issue 021) and may rotate the session id (issue 019). The same-session binding derives from the single-use `state`/PKCE/`nonce` transaction record (issue 017); the link commits only when the callback's session equals the initiating session.
- **Anti-Patterns**: MUST NOT commit a link without fresh re-auth; MUST NOT bind an identity/token to any session other than the initiating one; MUST NOT accept a replayed or cross-session callback; MUST NOT rely on prior authentication or `SameSite` alone (mutating-route CSRF control applies, SECURITY §3).
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Account-linking is a classic confused-deputy/login-CSRF trap where binding mistakes are directly exploitable for takeover; use the model with the strongest adversarial reasoning on session/OAuth binding. Mandatory human security review before merge.
