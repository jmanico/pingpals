# Requirement: API client (cookie-session, CSRF header, race-safe fetching)

## Metadata
- **ID**: REQ-FE-057
- **Title**: Frontend API client over HttpOnly cookie session with CSRF protection and race-safe data fetching
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Security

## Requirement
- **Description**: The frontend MUST provide a single API client that authenticates exclusively via the HttpOnly, Secure, SameSite session cookie. It MUST NOT read, write, or hold session identifiers or bearer tokens in `localStorage`, `sessionStorage`, or any other script-accessible store. Every state-changing request (`POST`/`PUT`/`PATCH`/`DELETE`) MUST carry the anti-CSRF token (synchronizer or double-submit header) established in issue 015. All data fetching performed in `useEffect` MUST guard against race conditions with an `AbortController` or an ignore flag and MUST clean up on unmount. Every API response MUST be passed through the Zod validation layer (issue 056) before use.
- **Rationale**: Centralizing transport enforces `SEC-1.2`/`INT-1.6` (no script-accessible session material), SECURITY §3 / issue 015 (CSRF defense beyond `SameSite` on mutating routes), and `FE-1.7` (race-safe, leak-free fetching) in one audited place rather than scattered `fetch` calls. The cookie is sent automatically by the browser; the client never touches the credential.
- **Design**: The client surfaces transport/auth errors to the UI as gentle, non-blaming messages (DESIGN §6 — "The royal messenger will try again.") rendered via the component library (064), and exposes loading states that can show the King Ping mascot / speech-bubble motif (DESIGN §5) during fetches. It carries no styling itself (logic-only module).

## Scope
- **Applies To**: Web App
- **Components**: React 19 SPA — shared `lib/api` client (fetch wrapper), CSRF-header injector, and a `useApi`/abortable-fetch hook consumed by all feature modules.
- **Actors**: Authenticated user (owner) — every request is implicitly scoped to the cookie's owning session; the server enforces per-user scoping (`SEC-2.2`).
- **Data Classification**: Restricted (requests/responses carry contact personal data, consent, tokens-by-reference); credentials never transit through script.

## Security Context
- **Defense Layer**: Architecture (transport centralization) + Authentication/Session handling + CSRF defense.
- **Threat(s) Addressed**: Session-token theft via XSS-readable storage (CWE-522/CWE-79), CSRF on mutating routes (CWE-352, OWASP A01:2021), `useEffect` race conditions producing stale/wrong-user renders and memory leaks (CWE-362). STRIDE: Spoofing, Tampering, Information Disclosure.
- **Trust Boundary**: Client-server edge. The client holds no authority; it presents what the API returns (ARCH Rule 1). CSRF defense is enforced server-side (015); the client's duty is to always emit the token on mutating requests.
- **Zero Trust Consideration**: The client assumes nothing from prior requests — every request rides the cookie and (for mutations) the CSRF token; responses are re-validated (056). Transport is TLS 1.3 only (`SEC-5.1`).

## Standards Alignment
- **OWASP ASVS**: V3 (session management), V4.2 (CSRF), V8.2 (no sensitive data in client storage), V13 (API)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: AC-12 (session), SC-23 (session authenticity), SI-10 (input validation)
- **NIST SP 800-207**: per-request authority server-side; client makes no trust decision
- **Regulatory**: n/a
- **Other**: `SEC-1.2`, `INT-1.6`, `FE-1.7`, SECURITY §3 (CSRF), issue 015

## Acceptance Criteria
1. **AC-01 (negative)**: Given any code path, when audited, then no session identifier or bearer token is ever written to or read from `localStorage`, `sessionStorage`, cookies-via-JS, or any script-accessible store. *(verbatim `SEC-1.2`/`INT-1.6`: tokens MUST NOT be placed in script-accessible storage.)*
2. **AC-02**: Given a `POST`/`PUT`/`PATCH`/`DELETE` request, when sent, then it includes the valid anti-CSRF token (header/double-submit per 015) and the request is accepted; a mutating request without the token is rejected 403 by the server with no write. *(verbatim SECURITY §3 / `FR-1.3`,`FR-6.2`,`PRIV-1.6`: a cross-site mutating request lacking a valid CSRF signal is rejected with 403 and performs no write.)*
3. **AC-03**: Given a `useEffect` that fetches data, when the component unmounts or its inputs change mid-flight, then the in-flight request is aborted (or its result ignored) and no state update occurs after unmount. *(verbatim `FE-1.7`: data fetching in `useEffect` MUST guard against race conditions and clean up on unmount.)*
4. **AC-04**: Given any API response, when received, then it is validated through the Zod layer (056) before use and a failed response fails closed (nothing unvalidated rendered).
5. **AC-05 (negative)**: Given two rapidly successive fetches for different inputs, when the slower (stale) one resolves last, then its result is discarded and the latest input's data is shown (no stale overwrite).

## Failure Behavior
- **On Invalid Input**: Mutations without a CSRF token are rejected server-side (403); the client surfaces a gentle error and does not retry blindly.
- **On System Error**: Fail closed for any security-relevant call (auth/consent/DSR) — a transport/timeout error never degrades to a weaker path (`SEC-2.3`, `NFR-1.6`); non-security reads MAY show a cached/last-known view where it exposes no Restricted data.
- **Alerting**: Repeated 401/403 or CSRF-rejection spikes MAY raise a frontend-health alert; no tokens or PII in the signal (`SEC-8.2`).

## Test Strategy
- **Unit Tests**: CSRF header attached on every mutating verb and absent-token path handled; storage audit asserts no token persistence; abortable-fetch hook cancels on unmount and ignores stale resolutions.
- **Integration Tests**: Full request cycle with a valid session cookie + CSRF token succeeds; a forged cross-site mutation is rejected; a component unmounting mid-fetch produces no post-unmount state update or console warning.
- **Security Tests**: Assert session material is unreachable from script; assert mutating requests fail without the CSRF token (maps to CSRF test in 015); confirm responses route through 056.
- **Compliance Tests**: n/a
- **Coverage Target**: ≥ 80% branch coverage of the API client and fetch hook.

## Dependencies
- **Upstream**: 054 (SPA scaffold), 015 (CSRF token mechanism), 019 (session management), 056 (Zod response validation).
- **Downstream**: 058–063 (every feature module fetches/mutates through this client).
- **External**: Browser `fetch`, `AbortController`, `crypto` — no third-party HTTP library without `SEC-9.1` vetting.

## Implementation Notes
- **Constraints**: One client module; no scattered raw `fetch`. Credentials ride the cookie only — never construct an `Authorization` header from script-held material. All requests over TLS 1.3 (`SEC-5.1`). The CSRF token source/format follows issue 015.
- **Anti-Patterns**: MUST NOT store/read tokens in script-accessible storage (`SEC-1.2`); MUST NOT omit the CSRF token on any mutating request; MUST NOT leave `useEffect` fetches unguarded (race/leak, `FE-1.7`); MUST NOT render unvalidated responses (use 056); MUST NOT make authorization decisions client-side (ARCH Rule 1); MUST NOT log tokens or PII (`SEC-8.2`).
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** This is well-bounded plumbing against a fixed contract (cookie session + CSRF + abortable fetch); breadth and consistency matter more than novel reasoning. Mandatory human security review of the no-script-storage and CSRF-on-mutation invariants before merge.
