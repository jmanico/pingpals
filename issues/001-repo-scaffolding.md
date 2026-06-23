# Requirement: Monorepo scaffolding for Flask API + React 19 client-only SPA

## Metadata
- **ID**: REQ-FND-001
- **Title**: Repository module layout, package manifests, and editor/ignore config for the Flask API and React 19 SPA
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Critical
- **Classification**: Functional

## Requirement
- **Description**: The repository MUST provide a single, coherent monorepo layout that hosts the Flask/REST API and the React 19 client-only SPA as two clearly separated modules, with package manifests (`pyproject.toml` and/or `requirements.txt` for the API; `package.json` for the SPA), an `.editorconfig`, and a `.gitignore`, such that each module can declare and pin its own dependencies and be built independently. The layout MUST realize the *logical* components of `ARCHITECTURE.md` (API service, Scheduler, Delivery worker, Outreach-link service, Integration adapters, Privacy/DSR, Persistence/KMS, AuthN/Session) as sensibly named source directories WITHOUT making any infrastructure decision left `TO BE DECIDED` (database, queue, KMS, cloud, push provider).
- **Rationale**: No source tree exists yet (bootstrap). Every downstream issue (auth, scheduler, delivery, persistence, tokens, tests) needs a fixed home and a manifest to pin into. A single deliberate layout prevents divergent ad-hoc structure and gives the CI gates (003), Docker hardening (002), and SBOM/pinning (004) a stable target. `CLAUDE.md` records "directory / module layout" as a placeholder this issue resolves at the *source* level only.
- **Design**: Per `DESIGN.md` §8 the `assets/` directory already holds brand art (`assets/pingpals-logo.png`); the SPA module references brand assets but does not relocate the canonical source art. Design-token file location (005) is reserved under the SPA module. No visual surface is built here.

## Scope
- **Applies To**: Both
- **Components**: Repository root tooling; Flask API module (logical sub-packages for AuthN/Session, Scheduler, Delivery worker, Outreach-link, Integration adapters, Privacy/DSR, Persistence/KMS, audit); React 19 SPA module.
- **Actors**: Developers and CI (build/test). No runtime end-user actor in scope.
- **Data Classification**: Internal (source layout and manifests carry no personal data and no secrets).

## Security Context
- **Defense Layer**: Architecture (separation of concerns; module boundaries that later carry trust boundaries)
- **Threat(s) Addressed**: Supply-chain and misconfiguration risk from unstructured projects; accidental secret commits (mitigated by `.gitignore` patterns); STRIDE: Tampering, Information Disclosure (via ignore rules that exclude `.env`, key material, build artifacts).
- **Trust Boundary**: Establishes the *file-system* separation between the client bundle (untrusted, ships to browsers) and the server (the single trust boundary of `ARCHITECTURE.md`); no client code may import server-only modules.
- **Zero Trust Consideration**: Layout enforces that no authorization or data-scoping logic lives in the SPA module (ARCH Dependency Rule 1); security invariants have a home only under the API module.

## Standards Alignment
- **OWASP ASVS**: V14.1 (build / configuration hygiene), V1.1 (secure SDLC structure)
- **OWASP AISVS**: n/a (no AI component)
- **NIST SP 800-53**: SA-15 (development process), CM-2 (baseline configuration)
- **NIST SP 800-207**: client/server separation supports per-request server-side enforcement
- **Regulatory**: n/a
- **Other**: `ARCHITECTURE.md` (Initial Architecture, Dependency Rules), `CLAUDE.md` (directory/module-layout placeholder)

## Acceptance Criteria
1. **AC-01**: Given a fresh clone, when a developer inspects the tree, then there are two top-level module roots (one API, one SPA), each with its own manifest, and a sensible sub-package per logical `ARCHITECTURE.md` component is present (even if empty/stub).
2. **AC-02**: Given the API manifest, when dependencies are listed, then they are version-pinnable (compatible with 004) and contain no infrastructure-coupling library that resolves a `TO BE DECIDED` choice (no concrete DB driver, queue client, KMS SDK, or cloud SDK is hard-committed as a required dependency).
3. **AC-03 (negative)**: Given `.gitignore`, when a developer stages `.env`, a virtualenv, `node_modules`, build output, or a key/secret file, then those paths are ignored and cannot be accidentally committed.
4. **AC-04 (negative)**: Given the SPA module, when its source is scanned, then it contains no server-only sub-package and no import path that reaches into the API module's internals (enforcing client/server separation).
5. **AC-05**: Given `.editorconfig`, when files are edited, then consistent indentation, charset (UTF-8), and final-newline rules apply across Python and TypeScript/JS files.

## Failure Behavior
- **On Invalid Input**: n/a (static scaffolding, no runtime input). A malformed manifest MUST fail the package-resolution step in CI (003) rather than silently producing a partial install.
- **On System Error**: Fail closed at build — a missing or unresolvable manifest blocks the build; no default/implicit dependency set is injected.
- **Alerting**: CI build failure on manifest resolution error (handled by 003).

## Test Strategy
- **Unit Tests**: n/a (no executable logic). A structural smoke check that required directories and manifests exist.
- **Integration Tests**: A bootstrap script/CI step installs API and SPA dependencies from the pinned manifests in a clean environment and exits non-zero on any resolution failure.
- **Security Tests**: Secret-scanning (003) runs clean; `.gitignore` excludes `.env`/key/secret patterns (assert the patterns are present).
- **Compliance Tests**: Confirm no `TO BE DECIDED` infrastructure dependency is committed (assert absence of concrete DB/queue/KMS/cloud SDKs in required deps).
- **Coverage Target**: ≥ 80% branch coverage applies to executable modules added later, not to scaffolding; the structural smoke check MUST pass.

## Dependencies
- **Upstream**: None (this is the foundation issue).
- **Downstream**: 002 (Docker multi-stage targets these module roots), 003 (CI runs against these manifests), 004 (SBOM/pinning reads these manifests), 005 (design tokens live under the SPA module), and effectively every implementation issue.
- **External**: None committed. Build/run/test commands remain `[PLACEHOLDER]` per `CLAUDE.md` and are NOT decided here.

## Implementation Notes
- **Constraints**: Stack is fixed (Flask/REST, React 19 client-only, Docker) and MUST NOT be changed. Keep every undecided infrastructure choice behind a module/interface boundary and default to the most restrictive option; reference the relevant DECISION issue rather than resolving it. Build/run/test command definitions are out of scope (placeholder).
- **Anti-Patterns**: MUST NOT add a database engine, queue/broker client, KMS vendor SDK, push provider SDK, or cloud SDK as a committed dependency (those are `TO BE DECIDED` in `ARCHITECTURE.md`). MUST NOT place any authorization/data-scoping code or secrets in the SPA module. MUST NOT commit `node_modules`, virtualenvs, build artifacts, or `.env` files. MUST NOT enable Flask debug mode or any debug server in the layout defaults (`SEC-9.x`, SECURITY §8).
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Mechanical, convention-driven scaffolding with well-known monorepo patterns and low adversarial-reasoning demand; a strong code-generation generalist is sufficient. Human review MUST confirm no `TO BE DECIDED` infrastructure leaked into a manifest and that client/server separation holds.
