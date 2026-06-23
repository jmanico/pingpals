# Requirement: CSRF protection on all state-changing routes

## Metadata
- **ID**: REQ-BE-015
- **Title**: Anti-CSRF enforcement beyond SameSite for every mutating request
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Critical
- **Classification**: Security

## Requirement
- **Description**: Because sessions are carried in cookies, `SameSite` alone is insufficient; the API MUST protect every state-changing REST request (`POST`/`PUT`/`PATCH`/`DELETE`) against cross-site request forgery by an affirmative control beyond `SameSite` — either an anti-CSRF token (synchronizer or double-submit) or strict request-time `Origin`/`Sec-Fetch-Site` enforcement against an exact-match allowlist. This control is distinct from the CORS/`Origin`-reflection response policy (issue 008 / SECURITY.md §1), which governs response policy rather than request authenticity. The control MUST fail closed: a missing, malformed, or unverifiable CSRF signal MUST deny the request.
- **Rationale**: Anchored in SECURITY.md §3 (CSRF defense on mutating routes), `SEC-2.3` (fail closed). Cookie-borne sessions are auto-attached by the browser on cross-site requests, so without an affirmative anti-CSRF control an attacker page could trigger contact deletion, consent withdrawal, or erasure on behalf of a logged-in user (`FR-1.3`, `FR-6.2`, `PRIV-1.6`). `SameSite` mitigates but does not fully close this (e.g. same-site subresource and edge-case navigations), so a second affirmative signal is required.
- **Design**: No user-facing surface; a rejected forged request returns a gentle, non-blaming `403` (DESIGN §6) without disclosing the token mechanism.

## Scope
- **Applies To**: Both (server enforces; the SPA supplies the token / sends same-origin requests).
- **Components**: Flask API service — CSRF middleware/enforcer (token issuance + verification or `Origin`/`Sec-Fetch-Site` allowlist check) on all mutating routes; the React SPA includes the token or relies on same-origin enforcement.
- **Actors**: Authenticated user (legitimate cross-origin attacker is the threat); any cross-site page attempting a forged mutation.
- **Data Classification**: Restricted (mutations affect contacts, consent, erasure); Confidential (session cookie that the attack abuses).

## Security Context
- **Defense Layer**: Architecture + Request Authenticity (anti-CSRF).
- **Threat(s) Addressed**: Cross-Site Request Forgery (CWE-352, OWASP A01:2021 broken access control), forged destructive mutations (contact delete, consent withdrawal, erasure). STRIDE: Spoofing, Tampering, Elevation of Privilege.
- **Trust Boundary**: The Flask boundary on mutating requests — request authenticity is verified independently of the session cookie's mere presence.
- **Zero Trust Consideration**: A valid session cookie is not trusted as proof the user intended the request; an affirmative, per-request CSRF signal must accompany every mutation, and its absence/invalidity fails closed.

## Standards Alignment
- **OWASP ASVS**: V4.2.2 (CSRF defenses), V3.5 (token-based session/CSRF)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SC-23 (session authenticity), AC-3 (access enforcement)
- **NIST SP 800-207**: per-request verification of intent, no trust from ambient cookie
- **Regulatory**: GDPR Art. 32 (preventing unauthorized processing) — protects consent withdrawal/erasure from forgery
- **Other**: SECURITY.md §3; OWASP CSRF Prevention Cheat Sheet; `SEC-2.3`, `FR-1.3`, `FR-6.2`, `PRIV-1.6`

## Acceptance Criteria
1. **AC-01 (verbatim SECURITY.md §3 CSRF clause)**: Given a cross-site `POST`/`DELETE` to a mutating endpoint (for example contact delete, consent withdrawal, erasure) carrying a valid session cookie but no valid CSRF signal, when received, then it is rejected with `403` and performs no write.
2. **AC-02**: Given a legitimate same-origin mutating request with a valid anti-CSRF token (or passing the exact-match `Origin`/`Sec-Fetch-Site` allowlist), when received, then it is accepted and processed.
3. **AC-03 (negative)**: Given a mutating request with a missing, malformed, or unverifiable CSRF signal, when evaluated, then it is denied (fail closed, `SEC-2.3`) and no write occurs.
4. **AC-04 (negative)**: Given a state-changing route (`POST`/`PUT`/`PATCH`/`DELETE`), when it is registered without CSRF enforcement, then a test/lint gate flags it (no mutating route may opt out).
5. **AC-05**: Given the CSRF control and the CORS policy (issue 008), when both are evaluated, then they are independent — passing CORS does not satisfy CSRF and vice versa (distinct concerns).

## Failure Behavior
- **On Invalid Input**: Missing/invalid CSRF signal → `403`, no write, audit a denial where appropriate.
- **On System Error**: Fail closed — if the CSRF signal cannot be verified (e.g. token store unavailable), deny the mutation.
- **Alerting**: A spike in CSRF rejections (especially against destructive routes) raises a security alert.

## Test Strategy
- **Unit Tests**: Token issue/verify; `Origin`/`Sec-Fetch-Site` exact-allowlist matcher; deny on missing/malformed signal.
- **Integration Tests**: Forged cross-site `POST`/`DELETE` with valid cookie but no token → `403`, no write (the verbatim AC); legitimate same-origin mutation succeeds.
- **Security Tests**: Cross-site forgery simulation against contact-delete, consent-withdrawal, and erasure routes; assert no write; route-coverage test asserting every mutating endpoint is protected.
- **Compliance Tests**: Evidence that all `POST`/`PUT`/`PATCH`/`DELETE` routes are enrolled in CSRF enforcement.
- **Coverage Target**: ≥ 80% branch coverage of the CSRF enforcer.

## Dependencies
- **Upstream**: 007 (Flask skeleton, `SECRET_KEY` for token signing), 008 (HTTP boundary — CORS is the distinct sibling policy), auth/session issues (session context for synchronizer tokens).
- **Downstream**: All mutating endpoints — contact CRUD (`FR-1.3`), consent grant/withdrawal (`FR-6.2`), erasure/DSR (`PRIV-1.6`), category/cadence mutations.
- **External**: None (in-process token mechanism; no external dependency without `SEC-9.x` vetting).

## Implementation Notes
- **Constraints**: Token signing uses the secret-store `SECRET_KEY` (issue 007), rotatable per `SEC-3.x`. If using `Origin`/`Sec-Fetch-Site`, the allowlist is exact-match and distinct from CORS configuration. Enforcement must be mandatory middleware so no mutating route can silently bypass it.
- **Anti-Patterns**: MUST NOT rely on `SameSite` alone; MUST NOT treat a valid session cookie as intent; MUST NOT conflate CORS (response policy) with CSRF (request authenticity); MUST NOT fail open when the token/signal cannot be verified; MUST NOT exempt destructive routes.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** CSRF defenses have well-known but easy-to-misimplement edge cases (double-submit binding, `Origin` vs. `Referer` reliability, route coverage gaps) that leave destructive mutations forgeable. Favor the model with stronger adversarial reasoning on request-authenticity bypasses. Mandatory human security review of the chosen mechanism and route coverage before merge.
