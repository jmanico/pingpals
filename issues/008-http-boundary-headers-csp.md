# Requirement: HTTP boundary hardening — TLS 1.3, strict CSP, security headers, CORS

## Metadata
- **ID**: REQ-BE-008
- **Title**: HTTP boundary controls — TLS 1.3 enforcement, strict CSP, hardening headers, narrow CORS
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Critical
- **Classification**: Security

## Requirement
- **Description**: The API MUST enforce a hardened HTTP boundary: all traffic MUST use TLS 1.3 and plaintext transport MUST be rejected (not silently redirected); a strict Content Security Policy MUST be sent on every document/response (no inline script, no inline event handlers, no `eval`, no `data:` or wildcard script sources); the response MUST carry `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` (or stricter), and a restrictive `Permissions-Policy` by default; CORS MUST use a narrow, explicit origin allowlist matched exactly and MUST NOT reflect `Origin` or send `Access-Control-Allow-Origin: *` for credentialed routes; and error responses MUST be least-information (no stack traces, framework banners, or internal hostnames).
- **Rationale**: These headers are the browser-enforced half of the application's defense in depth: the strict CSP backstops XSS even if a sink is missed, HSTS prevents downgrade, `nosniff` blocks MIME confusion, and an exact CORS allowlist prevents a malicious origin from reading credentialed responses. Anchored in SECURITY.md §1 (HTTP boundary), `SEC-5.1` (TLS 1.3, reject plaintext), `FE-1.4` (strict CSP friendliness), `NFR-1.3` (no internal detail to clients).
- **Design**: The CSP and headers MUST permit the DESIGN.md font/asset strategy (Subresource Integrity or self-hosted per `FE-1.8`/DESIGN §4.1) without inline script. No user-facing copy; gentle error pages per DESIGN §6 still leak no internals.

## Scope
- **Applies To**: Both (server emits the policy; the React SPA must run under it).
- **Components**: Flask API service — a response/header middleware (after-request hook), CORS configuration, TLS-termination policy contract.
- **Actors**: Authenticated user's browser; any cross-origin caller (rejected unless allowlisted).
- **Data Classification**: Restricted personal data transits these responses; the controls protect its transport and reading.

## Security Context
- **Defense Layer**: Architecture + Output/Transport hardening (browser-enforced policy).
- **Threat(s) Addressed**: XSS (CWE-79, mitigated by strict CSP), protocol downgrade / MITM (CWE-319 cleartext transmission; HSTS + TLS 1.3), MIME sniffing (CWE-430/`nosniff`), cross-origin data theft via permissive CORS (CWE-942), referrer leakage (CWE-200), information disclosure via error detail (CWE-209). STRIDE: Information Disclosure, Tampering, Spoofing.
- **Trust Boundary**: The client-server edge — every response leaving the Flask boundary carries the enforced policy; the boundary refuses plaintext.
- **Zero Trust Consideration**: No origin is trusted by network position; CORS is an explicit exact-match allowlist and the boundary re-asserts transport and policy on every response rather than assuming an earlier hop set them.

## Standards Alignment
- **OWASP ASVS**: V14.4 (HTTP security headers), V14.5 (CORS), V9.1 (TLS), V3.4 (cookie/transport)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SC-8 (transmission confidentiality/integrity), SC-23 (session authenticity), SI-10 (input handling at boundary)
- **NIST SP 800-207**: no trust by network location; per-response policy enforcement
- **Regulatory**: GDPR Art. 32 (security of processing — encryption in transit)
- **Other**: SECURITY.md §1; OWASP REST Security & API Security Top 10; `SEC-5.1`, `FE-1.4`, `FE-1.8`, `NFR-1.3`

## Acceptance Criteria
1. **AC-01**: Given any client request, when the connection is plaintext HTTP, then the boundary rejects it rather than silently redirecting, and TLS connections negotiate TLS 1.3 (`SEC-5.1`).
2. **AC-02**: Given any served response, when headers are inspected, then a strict CSP is present with no inline script/handler allowance, no `eval`, and no `data:`/wildcard script source, plus HSTS, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` (or stricter), and a restrictive `Permissions-Policy`.
3. **AC-03**: Given a credentialed route, when an allowlisted origin calls it, then CORS responds with that exact origin; when a non-allowlisted origin calls, then the response neither reflects the origin nor sends `*`.
4. **AC-04 (negative)**: Given an inline `<script>` or inline `onclick` is introduced in any page, when loaded under the enforced CSP, then the browser blocks it (no inline execution path exists).
5. **AC-05 (negative)**: Given an unhandled error, when the response is returned, then it contains no stack trace, framework banner, or internal hostname (`NFR-1.3`).
6. **AC-06 (negative)**: Given a request from `https://evil.example` to a credentialed endpoint, when CORS is evaluated, then the cross-origin read is denied (no `Access-Control-Allow-Origin` echo).

## Failure Behavior
- **On Invalid Input**: A disallowed origin or a plaintext request is rejected; no credentialed data is returned cross-origin.
- **On System Error**: Fail closed — if the header/CSP middleware cannot apply the policy, the response is refused rather than served without policy.
- **Alerting**: A surge in CSP violation reports (if a report endpoint is configured) or in rejected-origin attempts MAY raise a security alert; not request-blocking on its own.

## Test Strategy
- **Unit Tests**: Header middleware emits exact expected header set; CORS allowlist matcher accepts only exact origins and rejects suffix/substring/`null`.
- **Integration Tests**: Boot the app and assert response headers on representative routes; assert plaintext request handling and TLS-version policy contract; assert credentialed CORS behavior for allowlisted vs. foreign origins.
- **Security Tests**: DAST header/CSP scan; CSP bypass attempt via inline script; CORS misconfiguration probe; SAST rule banning `Access-Control-Allow-Origin: *` on credentialed routes and `Origin` reflection.
- **Compliance Tests**: Config evidence capturing the enforced header values and CORS allowlist per environment.
- **Coverage Target**: ≥ 80% branch coverage of the header/CORS middleware.

## Dependencies
- **Upstream**: 007 (Flask skeleton — middleware mounts here).
- **Downstream**: 054 (React SPA must run CSP-clean — no inline script/handlers, SRI fonts), 015 (CSRF — §1 CORS policy is distinct from §3 request-authenticity), 055 (URL allowlist relies on no-inline-handler posture).
- **External**: TLS termination layer / reverse proxy (cloud `TO BE DECIDED`, DECISION 073) — TLS 1.3 enforcement contract documented behind that boundary; defaults to reject plaintext.

## Implementation Notes
- **Constraints**: TLS termination may sit in front of Flask (load balancer); where it does, the requirement is a contract on that layer plus app-level rejection of forwarded-plaintext signals — keep behind the hosting interface (DECISION 073), default to reject. CSP must be authored to permit DESIGN.md self-hosted/SRI fonts without `unsafe-inline`.
- **Anti-Patterns**: MUST NOT use `unsafe-inline`/`unsafe-eval` or `data:` in script-src; MUST NOT silently redirect plaintext to HTTPS in place of rejecting it where the spec requires rejection; MUST NOT reflect `Origin` or wildcard credentialed CORS; MUST NOT weaken HSTS with a short max-age in production.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** CSP authoring and CORS-credential semantics have subtle, high-impact failure modes (an overlooked `unsafe-inline` or reflected origin is directly exploitable); favor the model with stronger adversarial reasoning on browser security policy. Mandatory human security review of the final CSP and CORS allowlist before merge.
