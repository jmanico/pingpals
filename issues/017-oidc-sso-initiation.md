# Requirement: OIDC/OAuth authorization initiation (Authorization Code + PKCE) with single-use transaction state

## Metadata
- **ID**: REQ-AUTH-017
- **Title**: OIDC SSO / OAuth authorization-request initiation with PKCE, exact redirect-URI match, and bounded single-use transaction-state store
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Critical
- **Classification**: Security

## Requirement
- **Description**: The system MUST initiate every OIDC/OAuth flow (Google SSO login and all integration providers) using the Authorization Code flow with PKCE (`S256`); the implicit grant and the resource-owner password credentials grant MUST NOT be used. Each redirect URI MUST be matched by exact string comparison against a preregistered allowlist. For every initiation the system MUST generate and persist a per-flow transaction-state record holding the `state`, the PKCE `code_verifier`, the `nonce`, and the expected issuer (`iss`); the authorization request MUST carry the `state`, the `S256` `code_challenge`, and the `nonce`. This transaction state MUST be single-use and short-lived (expiring within a few minutes), MUST be consumed and deleted on the first matching callback, and a successful or expired entry MUST NOT be reusable. The pending-transaction store MUST be bounded; when the bound is reached the system MUST fail closed by rejecting new authorization initiations rather than growing without limit.
- **Rationale**: PKCE + exact redirect matching + per-flow `state`/`nonce` are the RFC 9700 baseline that defeats authorization-code interception, CSRF, and mix-up attacks. A single-use, expiring, bounded transaction store prevents `state`/PKCE replay and stops an attacker from exhausting storage by initiating many never-completed flows. This is the **initiation** half of the SSO flow; ID-token validation on the callback is issue 018, and session promotion is issue 019.
- **Design**: This is a backend AuthN-subsystem concern with no brand surface of its own; the user-visible "Sign in with Google" affordance follows `DESIGN.md` §7 (Royal Purple primary action). The initiation endpoint redirects the browser to the provider and stores no personal data in the transaction record.

## Scope
- **Applies To**: Both
- **Components**: AuthN/Session subsystem (authorization-initiation endpoint); transaction-state store (interface; backing store `TO BE DECIDED`); OAuth provider adapter (issue 022) supplies the per-adapter scope/redirect config.
- **Actors**: Anonymous user beginning login; Authenticated user beginning an integration link (re-auth path is issue 023).
- **Data Classification**: Confidential (session/transaction material: `state`, `code_verifier`, `nonce`). No contact PII.

## Security Context
- **Defense Layer**: Architecture (OAuth flow selection) + Input Validation (exact redirect-URI match) + Strict API
- **Threat(s) Addressed**: Authorization-code interception (CWE-294), CSRF on the OAuth flow (CWE-352), mix-up attacks, `state`/PKCE replay, open redirect via loose redirect matching (CWE-601), resource-exhaustion DoS on the pending-transaction store. STRIDE: Spoofing, Tampering, Repudiation, Denial of Service.
- **Trust Boundary**: Client-server edge plus the trust boundary with the external IdP/provider; the authorization response is untrusted until `state`/`iss` are validated.
- **Zero Trust Consideration**: No authorization response is trusted on arrival; the returned `state` and `iss` are matched against the server-held single-use transaction record before the callback (issue 018) proceeds. Network position grants nothing.

## Standards Alignment
- **OWASP ASVS**: V3 (session management), V51/V52 (OAuth/OIDC — authorization request, PKCE, redirect-URI validation)
- **OWASP AISVS**: n/a (no AI component)
- **NIST SP 800-53**: IA-2, IA-8 (identification/authentication), SC-5 (denial-of-service protection), AC-12
- **NIST SP 800-207**: per-request trust; no implicit trust of the authorization response
- **Regulatory**: GDPR Art. 32 (security of processing) — secure authentication of the data controller (the user)
- **Other**: RFC 9700 (OAuth 2.0 Security BCP), RFC 6749, RFC 7636 (PKCE); `INT-1.1`, `INT-1.2`, `INT-1.3`, `SEC-6.1`, SECURITY §2

## Acceptance Criteria
1. **AC-01**: Given a login or link initiation, when the authorization request is built, then it uses Authorization Code + PKCE (`S256`) and carries a fresh `state`, `code_challenge`, and `nonce`, and a transaction-state record is persisted with `state`/`code_verifier`/`nonce`/expected-`iss`.
2. **AC-02**: Given a callback whose redirect URI is matched against the preregistered allowlist, when matching is performed, then it succeeds only on exact string equality; a redirect URI differing by suffix, subpath, trailing slash, or query is rejected. *(verbatim `INT-1.2`: redirect URIs matched by exact string comparison.)*
3. **AC-03**: Given a transaction-state entry already consumed by a first matching callback, when the same `state`/PKCE entry is replayed, then it is rejected; given an entry past its expiry, when a callback arrives, then it is rejected and the pending entry has already been evicted. *(verbatim SECURITY §2 / `INT-1.3`: a `state`/PKCE entry replayed after first use or after expiry is rejected, and pending entries are evicted on expiry.)*
4. **AC-04 (negative)**: Given the pending-transaction store is at its configured bound, when a new authorization initiation is requested, then the initiation is rejected (fail closed) and no unbounded growth occurs.
5. **AC-05 (negative)**: Given a request that attempts the implicit grant or ROPC, when initiation is evaluated, then it is refused; only Authorization Code + PKCE is permitted.

## Failure Behavior
- **On Invalid Input**: Reject a non-allowlisted redirect URI or malformed initiation with HTTP 400, log an authorization-denial audit event (`SEC-8.1`) with a correlation id, and disclose no internal detail.
- **On System Error**: Fail closed — if the transaction-state record cannot be persisted, or the store is at its bound, or its integrity cannot be established, no authorization request is issued.
- **Alerting**: Alert on a sustained rate of rejected initiations from store saturation (possible exhaustion attack) and on transaction-store write failures.

## Test Strategy
- **Unit Tests**: `state`/`nonce`/`code_verifier` generation (fresh, unpredictable, sufficient entropy); `S256` challenge derivation; exact redirect-URI matcher (allow exact, reject near-matches); transaction-record lifecycle (create, single-use consume, expiry eviction, bound rejection).
- **Integration Tests**: Full initiation → provider-redirect path; callback consuming a valid entry once; replayed/expired entry rejected; store-bound saturation rejects new initiations.
- **Security Tests**: Redirect-URI exact-match fuzz corpus (maps to TEST-1.3 "redirect URI exact matching"); `state`/PKCE replay; pending-store exhaustion; rate-limit enforcement on the initiation/callback endpoints (`SEC-6.1`).
- **Compliance Tests**: Assert audit entries for authorization denials are written and attributable.
- **Coverage Target**: ≥ 80% branch coverage of the initiation/transaction-store module.

## Dependencies
- **Upstream**: 022 (OAuth provider adapter — per-adapter redirect/scope config), AuthN subsystem scaffold; DECISION issue for the transaction-state backing store (keep behind an interface, default to the most-restrictive single-use/bounded store).
- **Downstream**: 018 (ID-token validation consumes the stored `nonce`/expected `iss`), 019 (session promotion after a valid callback), 023 (account-linking re-auth reuses this initiation with a same-session binding).
- **External**: Google OIDC provider; later-phase OAuth providers; rate limiter (`SEC-6.1`).

## Implementation Notes
- **Constraints**: `state`/`nonce`/`code_verifier` MUST come from a CSPRNG. Redirect allowlist is a hard-coded/configured constant compared by `===`. Transaction store MUST enforce TTL and a hard cardinality bound; while the backing store is `TO BE DECIDED`, express it behind an interface and default to a bounded, single-use, expiring store. Initiation and callback endpoints are rate limited (`SEC-6.1`).
- **Anti-Patterns**: MUST NOT use the implicit or ROPC grant; MUST NOT match redirect URIs by prefix/suffix/regex/wildcard; MUST NOT reuse a transaction entry; MUST NOT place `state`/`nonce`/`code_verifier` in URLs that get logged, in browser-accessible storage, or in audit entries (`INT-1.6`); MUST NOT let the pending store grow unbounded.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** OAuth-initiation correctness is security-critical and full of subtle replay/mix-up/redirect-matching edge cases; use the model with the strongest adversarial reasoning on protocol state machines. Mandatory human security review before merge.
