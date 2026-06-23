# Requirement: CI gate set — SAST, SCA, secret-scanning, dependency checks, coverage

## Metadata
- **ID**: REQ-FND-003
- **Title**: Merge-blocking CI pipeline enforcing TEST-1.6 / SEC-9.2 security gates and the ≥80% coverage gate
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Critical
- **Classification**: Security

## Requirement
- **Description**: CI MUST run, on every pull request and on the default branch, the full gate set: **SAST** (static analysis), **SCA** (software composition analysis), **secret-scanning**, and **dependency checks**, plus a **statement-coverage gate of ≥80%** (`TEST-1.1`). The pipeline MUST **block merge** on any gate failure or on any **newly introduced high-severity finding**. Gates MUST fail closed: an indeterminate, errored, or skipped gate MUST be treated as a failure, not a pass. The pipeline MUST be authored generically/config-driven so the specific CI provider remains undecided (`TO BE DECIDED`) behind a thin provider-agnostic definition.
- **Rationale**: `TEST-1.6` is the canonical CI-gate requirement (`SEC-9.2` is its subset); `CLAUDE.md` makes passing these gates part of the Definition of Done. Without an enforced, merge-blocking pipeline, security regressions, leaked secrets, vulnerable dependencies, and untested code reach `main`. Coverage ≥80% (`TEST-1.1`) is a hard CI gate.
- **Design**: No UI. The pipeline is invisible to end users but gates every change. User-facing error tone (`DESIGN.md` §6) does not apply; CI output is developer-facing and MUST give actionable, non-ambiguous failure messages.

## Scope
- **Applies To**: Both
- **Components**: CI workflow definition; SAST runner, SCA/dependency scanner, secret scanner, coverage reporter — all invoked against the API and SPA modules (001) and the hardened images (002).
- **Actors**: Developers (PR authors), CI service account, reviewers/merge gate.
- **Data Classification**: Internal. CI logs MUST NOT contain secrets or personal data (`SEC-8.2`, `NFR-1.3`).

## Security Context
- **Defense Layer**: Architecture / SDLC pipeline controls (shift-left enforcement)
- **Threat(s) Addressed**: Vulnerable/abandoned dependencies (CWE-1104, A06:2021), committed secrets (CWE-798), injection/insecure-code patterns caught by SAST (broad A03/A01), untested code paths. STRIDE: Tampering, Information Disclosure, Elevation of Privilege via supply chain.
- **Trust Boundary**: The merge gate into `main` — the boundary between proposed and accepted code. Nothing crosses it without passing the gates.
- **Zero Trust Consideration**: No change is trusted on author identity or prior green builds; every PR is independently re-scanned. A skipped or errored scan is denied (fail closed), never assumed safe.

## Standards Alignment
- **OWASP ASVS**: V1.14 (secure pipeline), V14.2 (dependency management)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SA-11 (developer testing & evaluation), RA-5 (vulnerability scanning), SA-15
- **NIST SP 800-207**: continuous verification of artifacts before promotion
- **Regulatory**: n/a
- **Other**: SECURITY §8 (CI/CD safety), `TEST-1.6` (canonical), `SEC-9.2`, `SEC-9.1`, `SEC-3.2`, `TEST-1.1`

## Acceptance Criteria
1. **AC-01**: Given a PR, when CI runs, then SAST, SCA, secret-scanning, dependency checks, and the coverage report all execute and report a pass/fail status.
2. **AC-02 (verbatim `TEST-1.6`)**: Given a PR that introduces a newly introduced high-severity finding (SAST or SCA) or fails any gate, when CI evaluates merge eligibility, then merge is blocked.
3. **AC-03 (negative)**: Given a commit containing a secret-shaped string (API key, private key, token), when secret-scanning runs, then the gate fails and merge is blocked. *(maps `SEC-3.2`: secret-scanning gate in CI.)*
4. **AC-04 (negative)**: Given statement coverage below 80%, when the coverage gate evaluates, then the build fails. *(verbatim `TEST-1.1`: ≥80% enforced as a CI gate.)*
5. **AC-05 (negative)**: Given a gate that errors out or is skipped, when CI evaluates results, then the overall result is failure (fail closed) — never a silent pass.
6. **AC-06**: Given the CI definition, when reviewed, then no single CI provider is hard-required by the security logic; the provider remains substitutable behind a config-driven definition (`TO BE DECIDED`).

## Failure Behavior
- **On Invalid Input**: A malformed scan config MUST fail the pipeline, not skip the gate.
- **On System Error**: Fail closed — scanner timeout, crash, or unavailable result blocks merge; the pipeline MUST NOT degrade to a passing state.
- **Alerting**: Gate failures surface on the PR and to the author; repeated secret-scan hits SHOULD notify a security channel (destination `TO BE DECIDED`).

## Test Strategy
- **Unit Tests**: n/a for the pipeline itself; validate the pipeline config parses and lints.
- **Integration Tests**: A deliberately vulnerable dependency, a planted secret, an insecure code pattern, and an under-covered module each, in a test PR, cause the corresponding gate to fail (each is a separate fixture).
- **Security Tests**: Confirm the four security gates run against both API and SPA modules; confirm fail-closed on a forced scanner error.
- **Compliance Tests**: CI produces durable evidence (logs/artifacts) that each gate ran and its result, retained for audit (`TEST-1.6`).
- **Coverage Target**: The coverage gate itself enforces ≥80% statements project-wide; the pipeline config logic is validated by the integration fixtures above.

## Dependencies
- **Upstream**: 001 (modules/manifests to scan), 002 (images to scan), 004 (pinned deps + SBOM feed SCA).
- **Downstream**: Every implementation issue relies on this gate as part of Definition of Done; security/privacy test suites (e.g. `TEST-1.3`/`TEST-1.4` consumers) run here.
- **External**: SAST/SCA/secret-scanning tooling and a CI provider — all `TO BE DECIDED`; keep behind a config-driven, provider-agnostic definition.

## Implementation Notes
- **Constraints**: Provider-agnostic; no provider-locked feature is load-bearing for the security gates. "Newly introduced high-severity" requires a baseline/diff mechanism so pre-existing findings do not mask new ones — implement diff-aware gating. Coverage gate measures statements (`TEST-1.1`).
- **Anti-Patterns**: MUST NOT allow `continue-on-error` / soft-fail on any security or coverage gate; MUST NOT let an errored or skipped scan count as a pass (fail closed); MUST NOT print secrets or personal data into CI logs; MUST NOT hard-couple the security logic to one CI vendor.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Pipeline wiring and tool configuration is a broad, well-documented integration task suited to a strong generalist; the security policy (fail-closed, diff-aware high-severity blocking) is explicit and checkable. Human review MUST confirm gates are genuinely merge-blocking and fail closed.
