# Requirement: Hardened Flask application skeleton (app-factory + blueprints)

## Metadata
- **ID**: REQ-BE-007
- **Title**: Hardened Flask app-factory skeleton with safe defaults
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Critical
- **Classification**: Security

## Requirement
- **Description**: The backend MUST be a Flask application constructed via an application factory (`create_app(config)`) that registers REST endpoints as blueprints, runs stateless behind cookie sessions, and ships with hardened defaults: `debug` MUST be `False` in any non-development build (the Werkzeug interactive debugger and its PIN MUST NOT be reachable in any deployed environment), and `SECRET_KEY` MUST be loaded at startup from the secret store (never hard-coded, never committed, never baked into the image or build args) and MUST be rotatable per `SEC-3.x`. Jinja autoescaping MUST remain enabled. The factory MUST fail closed at startup if `SECRET_KEY` is absent or `debug` would be true in a non-dev build.
- **Rationale**: The Werkzeug debugger grants remote code execution if exposed, and a hard-coded or weak `SECRET_KEY` lets an attacker forge session/CSRF material. A disciplined app-factory + blueprint layout is the structural precondition for every later boundary control (headers/CSP issue 008, validation 009, authz 014, CSRF 015). Anchored in SECURITY.md §8 "Flask hardening" and §2 (cookie sessions), `SEC-3.2` (no secrets in source/images), `SEC-4.2` (Jinja autoescape), `NFR-1.3` (no internal detail to clients).
- **Design**: No user-facing surface; this is the server scaffold that DESIGN.md tokens and the React SPA (issue 054) sit atop. Error responses stay gentle and non-blaming per DESIGN.md §6 without leaking internal state.

## Scope
- **Applies To**: API
- **Components**: Flask API service (app factory, blueprint registry, config loader, secret-store adapter interface).
- **Actors**: Authenticated user (sessions are cookie-borne); operators/CI provisioning the runtime.
- **Data Classification**: Confidential (`SECRET_KEY`, session-signing material). The skeleton stores no Restricted personal data itself.

## Security Context
- **Defense Layer**: Architecture (secure-by-default application bootstrap).
- **Threat(s) Addressed**: RCE via exposed Werkzeug debugger (CWE-489 active debug code), session/CSRF forgery via weak/known signing key (CWE-798 hard-coded credentials, CWE-330 insufficient randomness), information disclosure via debug tracebacks (CWE-215). STRIDE: Elevation of Privilege, Spoofing, Information Disclosure.
- **Trust Boundary**: The client-server edge — the Flask app is the single trust boundary (ARCHITECTURE.md). This issue establishes that the boundary process itself starts in a safe state.
- **Zero Trust Consideration**: The factory trusts no ambient configuration: it independently verifies that `debug` is false and a strong secret is present before serving any request, failing closed if either invariant cannot be established.

## Standards Alignment
- **OWASP ASVS**: V14.1 (build/deploy config), V14.2 (dependency & debug surface), V3 (session management foundations)
- **OWASP AISVS**: n/a (no AI component)
- **NIST SP 800-53**: CM-6 (configuration settings), CM-7 (least functionality), SA-15 (development process)
- **NIST SP 800-207**: fail-closed startup; no implicit trust of environment
- **Regulatory**: n/a
- **Other**: SECURITY.md §8 (Flask hardening), §2; `SEC-3.2`, `SEC-4.2`, `NFR-1.3`

## Acceptance Criteria
1. **AC-01**: Given the app is built for any non-dev configuration, when it starts, then `app.debug` is `False` and the Werkzeug interactive debugger/PIN is not reachable on any route.
2. **AC-02**: Given `SECRET_KEY` is supplied by the secret-store adapter, when the factory runs, then the key is loaded into config from that source and never read from a literal, environment-baked image layer, or build arg.
3. **AC-03 (negative)**: Given `SECRET_KEY` is missing/empty, when `create_app` runs for a non-dev config, then startup fails closed with a non-disclosing error and the app does not begin serving requests.
4. **AC-04 (negative)**: Given a non-dev config that would set `debug=True`, when `create_app` runs, then it raises and refuses to start rather than serving with the debugger enabled.
5. **AC-05**: Given any template render, when output contains user-influenced strings, then Jinja autoescaping is active (not disabled globally or per-template) so HTML is not constructed from untrusted strings (`SEC-4.2`).
6. **AC-06 (negative)**: Given an unhandled server error in production config, when a response is returned, then it contains no stack trace, framework banner, or internal hostname (`NFR-1.3`).

## Failure Behavior
- **On Invalid Input**: Misconfiguration (missing secret, debug-on) is treated as invalid startup input: refuse to start, emit a least-information log line (no secret values).
- **On System Error**: Fail closed — the app does not serve if a security-critical config invariant is unmet.
- **Alerting**: A failed-closed startup MUST surface to the deploy pipeline/operational channel; repeated boot failures raise an alert.

## Test Strategy
- **Unit Tests**: `create_app` with/without `SECRET_KEY`; dev vs non-dev `debug` resolution; assert autoescaping enabled; assert blueprints registered exactly once.
- **Integration Tests**: Boot the app under a production-like config; assert no debugger route, no PIN endpoint, generic error page for a forced 500.
- **Security Tests**: SAST rule for `debug=True` and literal `SECRET_KEY`; secret-scanning gate (`SEC-3.2`) over the repo and built image layers; probe for `/console` / Werkzeug debugger.
- **Compliance Tests**: Config-validation evidence that debug is off and secret originates from the secret store in every non-dev profile.
- **Coverage Target**: ≥ 80% branch coverage of the factory/config module.

## Dependencies
- **Upstream**: 069 (DECISION: database engine — repository wiring), 072 (DECISION: KMS/secret-store vendor; consumed via interface here).
- **Downstream**: 008 (HTTP boundary headers/CSP), 009 (input validation), 010 (persistence/user scoping), 014 (authorization PDP), 015 (CSRF) — all mount on this skeleton.
- **External**: Secret store / KMS (vendor `TO BE DECIDED`, behind an interface defaulting to deny when unavailable).

## Implementation Notes
- **Constraints**: Pure-Python Flask; secret loaded via an interface so the KMS/secret-store vendor stays `TO BE DECIDED` (DECISION 072). Keep the runtime image free of build toolchain and debug servers, non-root (SECURITY.md §8 Docker hardening — packaged in a separate deploy issue, referenced not resolved here).
- **Anti-Patterns**: MUST NOT hard-code `SECRET_KEY` or read it from a checked-in file; MUST NOT enable `debug=True` outside an explicit local-dev profile; MUST NOT disable Jinja autoescaping; MUST NOT leak tracebacks/banners to clients; MUST NOT register routes outside the blueprint structure (keeps authz/CSRF enforcement uniform).
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** This is a well-bounded, convention-driven scaffolding task with established Flask hardening patterns; a capable general model implements it efficiently. Mandatory human review confirms the secret-store interface and the debug/secret fail-closed checks before merge.
