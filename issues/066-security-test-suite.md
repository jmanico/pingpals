# Requirement: Security test suite (cross-user isolation, redirect URI, URL scheme, token non-exposure, webhook signature)

## Metadata
- **ID**: REQ-TEST-066
- **Title**: Mandatory security test cases for the TEST-1.3 control set
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Security

## Requirement
- **Description**: The test suite MUST include security test cases that cover, at minimum: cross-user authorization isolation (`SEC-2.2`), OAuth redirect-URI exact matching (`INT-1.2`), outreach-URL scheme rejection (`FR-6.4`), token non-exposure (`INT-1.6`), and webhook signature rejection (`SEC-7.1`). Each control MUST have explicit positive and negative cases, and these cases MUST run in CI as part of the blocking gate (issue 003) on the harness (issue 065).
- **Rationale**: `TEST-1.3` enumerates exactly these five security control areas as mandatory test coverage. These are the highest-leverage exploit surfaces (BOLA/cross-tenant, open redirect, XSS via deep links, token leakage, webhook forgery); asserting them in CI is how the corresponding controls stay enforced over time.
- **Design**: Per `DESIGN.md`, no end-user UI; the suite produces developer/CI evidence. Test assertions MUST NOT print captured tokens or PII (`SEC-8.2`).

## Scope
- **Applies To**: Both
- **Components**: Backend API endpoints (per-user data routes, OAuth callback, webhook receivers), the server outreach-link service (043) and the client `validateAndSanitizeUrl` (055), and log/response sinks for token-exposure checks.
- **Actors**: Two distinct authenticated users (for isolation tests), an unauthenticated attacker, a forging webhook sender — all simulated.
- **Data Classification**: Restricted (tests exercise contact data and tokens with synthetic values).

## Security Context
- **Defense Layer**: Architecture / Verification (asserts Input Validation, AuthZ, and Encoding controls remain in force).
- **Threat(s) Addressed**: Broken object/function-level authorization (CWE-639/BOLA/BFLA, OWASP API1/API5), open redirect / host spoofing (CWE-601), XSS via `javascript:`/`data:` deep links (CWE-79, A03:2021), sensitive-data exposure of tokens (CWE-522/CWE-200), webhook forgery & replay (CWE-345). STRIDE: Spoofing, Tampering, Information Disclosure, Elevation of Privilege.
- **Trust Boundary**: Exercises the API edge (client-server), the OAuth callback boundary, and the inbound-webhook boundary — the suite verifies each boundary fails closed.
- **Zero Trust Consideration**: Tests assert that no request is trusted on prior auth or network position — cross-user access is denied per request, and provider/webhook input is rejected unless validated.

## Standards Alignment
- **OWASP ASVS**: V4.x (access control), V5.x (validation/encoding), V13/V14 (config & API)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: AC-3 (access enforcement), SI-10 (input validation), SC-8/SC-23 (transmission/session integrity), SA-11 (developer security testing)
- **NIST SP 800-207**: per-request authorization; deny-by-default verification
- **Regulatory**: GDPR Art. 32 (security of processing) — cross-user isolation protects third-party data subjects
- **Other**: `TEST-1.3`, `SEC-2.2`, `INT-1.2`, `FR-6.4`, `INT-1.6`, `SEC-7.1`

## Acceptance Criteria
[Each criterion MUST be independently testable.]

1. **AC-01 (cross-user isolation)**: Given user A's object id, when user B requests it on every data endpoint, then the response is not-found or forbidden and no data leaks. *(verbatim `SEC-2.2`: automated tests assert that cross-user access returns a not-found or forbidden response for every data endpoint.)*
2. **AC-02 (redirect URI)**: Given a callback whose redirect URI is not an exact-string match of a preregistered URI, when validated, then it is rejected; a registered URI with an extra path/query/suffix does not match. *(verbatim `INT-1.2`: redirect URIs MUST be matched by exact string comparison against a preregistered allowlist.)*
3. **AC-03 (outreach URL scheme)**: Given a `javascript:` or `data:` outreach URL, when rendered/validated, then it never reaches the DOM as an href and resolves to `"#"`; given `https://wa.me.evil.example/...`, then it is rejected to `"#"`. *(verbatim `FR-6.4`: a `javascript:`/`data:` URL never reaches the DOM as an href, and an `https://wa.me.evil.example/...` lookalike-host URL is rejected to `"#"`.)*
4. **AC-04 (token non-exposure)**: Given any access/refresh token, when responses, URLs, logs, browser history, and client-side storage are inspected after auth and integration flows, then no token appears in any of them. *(maps to `INT-1.6`: tokens MUST NOT appear in URLs, logs, browser history, or any client-side storage accessible to scripts.)*
5. **AC-05 (webhook signature)**: Given an inbound webhook with a missing or invalid provider signature, when received, then it is rejected and produces no processing; a replayed (stale timestamp/nonce) but validly-signed request is also rejected. *(maps to `SEC-7.1`: webhooks MUST verify provider signatures and reject unsigned/invalid requests, with replay mitigation.)*
6. **AC-06 (negative coverage)**: Given the suite, when run in CI, then absence of any one of the five mandated case groups fails the build (the suite is required, not optional).

## Failure Behavior
- **On Invalid Input**: A failing security assertion fails the CI gate and blocks merge; the report identifies the violated control without printing secrets.
- **On System Error**: Fail closed — an errored or skipped security test is treated as a failure, never a pass.
- **Alerting**: A regression in any TEST-1.3 case raises a security-gate failure on the PR.

## Test Strategy
- **Unit Tests**: URL-scheme rejection table (drives 055/043 cases); redirect-URI exact-match comparator; webhook signature verifier and replay window.
- **Integration Tests**: Cross-user matrix iterating every data endpoint with user A's ids under user B's session (asserts 404/403); OAuth callback with mismatched redirect URI; webhook receiver with forged/unsigned/replayed payloads.
- **Security Tests**: Token-exposure sweep — grep responses, logs, and client storage for token patterns after login and integration link; fuzz outreach URLs with a `javascript:`/`data:`/lookalike-host corpus.
- **Compliance Tests**: CI evidence that all five TEST-1.3 control groups executed and passed.
- **Coverage Target**: ≥80% branch coverage of the security-test helper modules; cross-user matrix MUST iterate 100% of data endpoints.

## Dependencies
- **Upstream**: 065 (harness/coverage gate), 010 (persistence user-scoping), 014 (authorization decision point), 017/018 (OIDC), 022 (OAuth adapter), 043 (server outreach-link service), 055 (`validateAndSanitizeUrl`), and any webhook receiver (later-phase 078; MVP applies to email-provider webhooks per `SEC-7.1`).
- **Downstream**: 003 (CI gate consumes these cases); the security posture of all data endpoints depends on AC-01 staying green.
- **External**: OAuth provider test doubles; webhook-signature signing keys (synthetic) for the verifier tests.

## Implementation Notes
- **Constraints**: The cross-user matrix MUST be generated from the route registry so new endpoints are automatically covered (otherwise AC-01's "every data endpoint" silently rots). Token-exposure checks MUST inspect actual log output and client storage, not just code review.
- **Anti-Patterns**: MUST NOT hand-maintain an endpoint list that drifts from the real routes; MUST NOT assert only the positive path (negative cases are mandatory); MUST NOT print captured tokens/PII in assertion messages; MUST NOT weaken a failing security test to "skip" to get CI green.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Security test design demands adversarial reasoning to construct meaningful negative/bypass cases (lookalike hosts, authority injection, replay, partial-match redirect URIs) rather than only happy paths; the stronger adversarial model reduces false confidence. Mandatory human security review of the negative-case corpus before merge.
