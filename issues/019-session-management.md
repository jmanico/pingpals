# Requirement: Cookie-based session management with privilege-transition rotation (fixation defense)

## Metadata
- **ID**: REQ-AUTH-019
- **Title**: HttpOnly/Secure/SameSite session cookies, idle + absolute lifetimes, server-side revocation, fresh session id on every privilege transition
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Critical
- **Classification**: Security

## Requirement
- **Description**: The system MUST store session tokens in HttpOnly, Secure, SameSite cookies; session identifiers and bearer tokens MUST NOT be placed in `localStorage`, `sessionStorage`, or any script-accessible store. Sessions MUST have both idle and absolute lifetimes and MUST be revocable server-side. A fresh, unpredictable session identifier MUST be issued on every privilege transition — successful authentication, completion of MFA step-up, and the OIDC/OAuth callback that promotes an anonymous session — and any pre-authentication or prior session MUST be invalidated server-side at that moment, to prevent session fixation. If a fresh identifier cannot be guaranteed at the transition, the request MUST fail closed and the session MUST be denied rather than reused.
- **Rationale**: Cookie-stored, script-inaccessible session ids resist XSS exfiltration; idle/absolute lifetimes and server-side revocation bound session lifetime and enable logout/erasure to terminate access. Rotating the identifier on every privilege transition (and invalidating the old one) defeats session fixation, where an attacker plants a known id that becomes authenticated after the victim logs in.
- **Design**: Backend session subsystem; no brand surface. Logout and "sign out everywhere" affordances follow `DESIGN.md` §7; revocation underpins endpoint-purge-on-logout in `FR-6.5`.

## Scope
- **Applies To**: Both
- **Components**: AuthN/Session subsystem (session issuance, store, revocation); API service (per-request session resolution); consumed by every authenticated endpoint.
- **Actors**: Anonymous user being promoted to authenticated; authenticated user during MFA step-up and on logout.
- **Data Classification**: Confidential (session identifiers and session material).

## Security Context
- **Defense Layer**: Architecture (session model) + Strict API (cookie attributes, server-side state)
- **Threat(s) Addressed**: Session fixation (CWE-384), session-id theft via XSS / script-accessible storage (CWE-79/CWE-522), session hijacking, failure to revoke (CWE-613 insufficient session expiration). STRIDE: Spoofing, Elevation of Privilege.
- **Trust Boundary**: Client-server edge — the cookie crosses the boundary; the server is the sole authority on session validity and lifetime.
- **Zero Trust Consideration**: Every request re-resolves the session server-side and re-checks idle/absolute lifetime and revocation; a prior authentication or a held cookie grants nothing once revoked or expired.

## Standards Alignment
- **OWASP ASVS**: V3 (session management — cookie attributes, fixation, lifetimes, revocation)
- **OWASP AISVS**: n/a (no AI component)
- **NIST SP 800-53**: AC-12 (session termination), SC-23 (session authenticity), IA-2
- **NIST SP 800-207**: per-request session verification; no implicit trust from prior auth
- **Regulatory**: GDPR Art. 32 — protecting access to personal data; logout/erasure must terminate sessions
- **Other**: OWASP Session Management Cheat Sheet; `SEC-1.2`, `SEC-1.3`, SECURITY §2

## Acceptance Criteria
1. **AC-01**: Given a session is established, when the cookie is set, then it carries HttpOnly, Secure, and SameSite attributes, and no session id or bearer token is written to any script-accessible storage.
2. **AC-02**: Given an active session, when its idle or absolute lifetime elapses, then it is no longer accepted; given server-side revocation (logout or admin/erasure action), then the session is immediately rejected on the next request.
3. **AC-03**: Given a privilege transition — successful authentication, MFA step-up completion, or the OIDC/OAuth callback promoting an anonymous session — when it occurs, then a fresh unpredictable session identifier is issued and the prior session is invalidated server-side.
4. **AC-04 (negative)**: Given a session identifier captured before authentication, when the same browser later logs in, then that pre-auth identifier is never valid as an authenticated session. *(verbatim SECURITY §2: a session identifier captured before authentication is never valid as an authenticated session after the same browser logs in.)*
5. **AC-05 (negative)**: Given a privilege transition where a fresh identifier cannot be guaranteed, when the transition is processed, then the request fails closed and the session is denied rather than reused.

## Failure Behavior
- **On Invalid Input**: A request with a missing/expired/revoked/unknown session is treated as unauthenticated (401), with no detail about why; no fallback to a weaker session.
- **On System Error**: Fail closed — if the session store is unreachable or a fresh id cannot be generated at a transition, deny rather than reuse or issue an unverified session.
- **Alerting**: Alert on a spike in failed session resolutions and on session-store unavailability; log session-fixation-prevention failures.

## Test Strategy
- **Unit Tests**: Cookie-attribute construction; idle vs. absolute lifetime expiry math; session-id entropy/unpredictability; revocation flips validity; rotation-on-transition produces a new id and invalidates the old.
- **Integration Tests**: Promote anon→authenticated session and assert id rotation + old-id invalidation; MFA step-up rotation; logout revokes server-side; expired session rejected; cross-request revocation.
- **Security Tests**: Session-fixation attempt (pre-auth id replayed after login is rejected); attempt to read the session cookie from script (blocked by HttpOnly); fuzz of stale/forged session ids.
- **Compliance Tests**: Assert logout/erasure produces session revocation and an audit entry (`SEC-8.1`).
- **Coverage Target**: ≥ 80% branch coverage of the session-issuance and revocation modules.

## Dependencies
- **Upstream**: 017 (initiation), 018 (ID-token validation gates the promotion this rotates on).
- **Downstream**: 021 (MFA step-up triggers a fresh session id via this module), 022/023 (OAuth callbacks promote sessions through this rotation), `FR-6.5` endpoint purge on logout, every authenticated endpoint (per-request session resolution).
- **External**: Session store (resolved: PostgreSQL-backed, server-side revocable — keep behind the session-store interface, defaulting to a server-side revocable store).

## Implementation Notes
- **Constraints**: Session ids from a CSPRNG; idle and absolute lifetimes both enforced server-side; revocation is authoritative and immediate. Backing store is resolved to PostgreSQL-backed and server-side revocable — express behind the session-store interface, defaulting to server-side state enabling revocation (a stateless-only token cannot be revoked and is non-compliant).
- **Anti-Patterns**: MUST NOT store session ids/bearer tokens in `localStorage`/`sessionStorage` or any script-accessible store; MUST NOT keep the same session id across a privilege transition; MUST NOT issue a session when a fresh id cannot be guaranteed; MUST NOT rely on `SameSite` as the sole CSRF defense (mutating-route CSRF tokens are a separate control, SECURITY §3).
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Session lifecycle and fixation defense are subtle, high-impact correctness work spanning cookie semantics and transition timing; use the model with the strongest adversarial reasoning on auth state machines. Mandatory human security review before merge.
