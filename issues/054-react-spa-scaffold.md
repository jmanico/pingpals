# Requirement: React 19 client-only SPA scaffold with secure-by-default posture

## Metadata
- **ID**: REQ-FE-054
- **Title**: React 19 client-only SPA scaffold (no SSR, strict CSP, no unsafe DOM patterns)
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Security

## Requirement
- **Description**: The system MUST provide a React 19, client-only Single Page Application scaffold that uses function components and hooks only, with no server-side rendering and no Node-specific runtime APIs. The scaffold MUST be wired for a strict Content Security Policy compatible build: no inline script, no inline event handlers, and no `eval`. `dangerouslySetInnerHTML` MUST NOT be used anywhere in the codebase. Props MUST NOT be spread onto DOM nodes. React keys MUST be generated with `crypto.randomUUID()` where a stable domain id is not available, and array index keys MUST NOT be used for dynamic lists. Any external script the app loads MUST use Subresource Integrity, or the asset MUST be self-hosted to satisfy the strict CSP. The scaffold MUST consume design tokens (issue 005) for all styling and MUST NOT hard-code visual values.
- **Rationale**: A secure-by-default foundation prevents whole classes of vulnerability (DOM XSS, prop-injection, CSP bypass) from ever entering the codebase, satisfying `FE-1.1`, `FE-1.4`, `FE-1.5`, `FE-1.6`, `FE-1.8` and the ARCHITECTURE Web client posture (client-only, no SSR, no Node APIs). Establishing this once means every downstream feature issue inherits the safe baseline rather than re-litigating it.
- **Design**: Per `DESIGN.md` §7 and §7.1, the scaffold establishes the Parchment (`--color-cream-50`) app background, white card surfaces, and the token pipeline (CSS custom properties / `tokens.ts`) that all components consume — never hard-coded hex. The app shell reserves placement for the King Ping mascot mark (DESIGN §2.1) as favicon/loading state and the crown divider motif (DESIGN §5) for section headers. Web fonts (Inter for UI, DESIGN §4) load via Subresource Integrity or self-hosted to satisfy CSP (`FE-1.8`, `FE-1.4`).

## Scope
- **Applies To**: Web App
- **Components**: React 19 SPA — application shell, build tooling, CSP/SRI wiring, lint rules enforcing the FE invariants, design-token import.
- **Actors**: Authenticated user (owner) — the scaffold renders only the owner's own data; no other actor.
- **Data Classification**: Internal (the scaffold itself holds no personal data; it is the container for Restricted data views built in later issues).

## Security Context
- **Defense Layer**: Architecture (secure-by-default frontend foundation) + Output Encoding posture.
- **Threat(s) Addressed**: DOM-based XSS via `dangerouslySetInnerHTML` (CWE-79, OWASP A03:2021), prop-spread injection onto DOM, CSP bypass via inline script/`eval` (CWE-95), supply-chain script tampering (CWE-494, mitigated by SRI). STRIDE: Tampering, Elevation of Privilege.
- **Trust Boundary**: Client render boundary. The SPA makes no authorization or data-scoping decisions (ARCH Dependency Rule 1); it presents what the API returns and enforces only render-time safety invariants.
- **Zero Trust Consideration**: The client trusts nothing from its own origin's bundle or third-party scripts without integrity verification; all dynamic data is treated as untrusted and rendered only through React's default text-escaping (never raw HTML).

## Standards Alignment
- **OWASP ASVS**: V5.3 (output encoding / injection prevention), V14.4 (HTTP security / CSP), V14.2 (dependency / SRI)
- **OWASP AISVS**: n/a (no AI component)
- **NIST SP 800-53**: SI-10 (input validation), SI-7 (software integrity / SRI), SC-18 (mobile/active code)
- **NIST SP 800-207**: client makes no trust decision; all authority server-side
- **Regulatory**: n/a
- **Other**: WHATWG CSP Level 3; `FE-1.1`, `FE-1.4`, `FE-1.5`, `FE-1.6`, `FE-1.8`; ARCHITECTURE Web client component

## Acceptance Criteria
1. **AC-01**: Given the SPA builds and runs, when inspected, then it is React 19, client-only (no SSR entry point), uses function components and hooks exclusively, and references no Node-specific runtime API.
2. **AC-02**: Given a strict CSP is served (issue 008), when the app loads, then no inline script, inline event handler, or `eval` is present and the app functions without CSP violations. *(verbatim `FE-1.4`: a strict Content Security Policy MUST be enforced.)*
3. **AC-03 (negative)**: Given the codebase, when scanned by a lint/CI rule, then no occurrence of `dangerouslySetInnerHTML` exists and the build fails if one is introduced. *(verbatim `FE-1.1`: `dangerouslySetInnerHTML` MUST NOT be used anywhere.)*
4. **AC-04 (negative)**: Given a component renders to a DOM node, when reviewed, then props are not spread onto that node (no `{...props}` on host elements). *(verbatim `FE-1.5`: Props MUST NOT be spread onto DOM nodes.)*
5. **AC-05**: Given a dynamic list, when rendered, then keys come from a stable domain id or `crypto.randomUUID()`, never the array index. *(verbatim `FE-1.6`: Array index keys MUST NOT be used for dynamic lists.)*
6. **AC-06 (negative)**: Given an external script is referenced without a Subresource Integrity attribute and not self-hosted, when the build runs, then it is rejected/flagged. *(verbatim `FE-1.8`: Any external script MUST use Subresource Integrity.)*
7. **AC-07**: Given any styled element, when inspected, then its visual values resolve from design tokens (issue 005), not hard-coded hex/px literals (DESIGN §7.1).

## Failure Behavior
- **On Invalid Input**: n/a at scaffold level (no data input); downstream issues handle data validation (056, 009).
- **On System Error**: Fail closed — a CSP violation or SRI mismatch blocks the offending resource rather than degrading to an unsafe load; the app surfaces a gentle non-blaming error (DESIGN §6) and does not render unverified content.
- **Alerting**: CSP violation reports (if a report endpoint is configured) MAY raise a frontend-health alert; SRI failures are build-blocking.

## Test Strategy
- **Unit Tests**: Lint-rule tests asserting `dangerouslySetInnerHTML`, prop-spread onto host nodes, and array-index keys are rejected; key-generation helper returns a valid UUID when no domain id is supplied.
- **Integration Tests**: Render the app shell under the production CSP and assert no inline-script/`eval` violation; assert fonts/external assets carry SRI or are same-origin.
- **Security Tests**: SAST/lint gate (TEST-1.6) blocks reintroduction of any prohibited pattern; verify CSP has no `unsafe-inline`/`unsafe-eval`/wildcard script source.
- **Compliance Tests**: CI evidence that the FE-1.x lint gate is enforced and blocking.
- **Coverage Target**: ≥ 80% statement coverage of any scaffold logic (helpers, key generator, error boundary).

## Dependencies
- **Upstream**: 005 (design tokens), 008 (HTTP boundary headers + CSP that the client must satisfy), 003 (CI pipeline to enforce the lint gate).
- **Downstream**: 055 (URL validator), 056 (Zod layer), 057 (API client), 058–064 (all frontend feature UIs build on this scaffold).
- **External**: React 19 runtime; a build toolchain — minimized and vetted per `SEC-9.1` before adoption.

## Implementation Notes
- **Constraints**: Client-only — no SSR, no Node-specific APIs (ARCHITECTURE Web client). Enforce the FE invariants as CI-blocking lint rules, not conventions. Strict CSP is the contract; do not introduce any pattern requiring `unsafe-inline`/`unsafe-eval`.
- **Anti-Patterns**: MUST NOT use `dangerouslySetInnerHTML` (`FE-1.1`); MUST NOT spread props onto DOM nodes (`FE-1.5`); MUST NOT use array index keys for dynamic lists (`FE-1.6`); MUST NOT add inline event handlers or `eval`; MUST NOT load third-party scripts without SRI; MUST NOT hard-code styling values (DESIGN §7.1); MUST NOT make any authorization/data-scoping decision client-side (ARCH Rule 1).
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Scaffolding is broad, pattern-heavy boilerplate where wide, consistent application of a fixed rule set across many files is the main demand. Mandatory human review that the CI lint gates actually block each prohibited pattern before merge.
