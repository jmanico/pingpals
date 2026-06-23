# Requirement: Test harness (unit + integration + e2e) with ≥80% coverage CI gate

## Metadata
- **ID**: REQ-TEST-065
- **Title**: Establish the unit/integration/end-to-end test harness and enforce ≥80% statement coverage as a CI gate
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Functional

## Requirement
- **Description**: The project MUST provide a runnable test harness covering unit, integration, and end-to-end (e2e) layers for both backend (Flask/REST) and frontend (React 19 SPA), and CI MUST enforce a minimum of 80% statement coverage as a blocking gate that fails the build below threshold. The harness MUST be wired into the CI pipeline (issue 003) so every PR runs the full suite and the coverage gate.
- **Rationale**: `TEST-1.1` mandates ≥80% statement coverage enforced as a CI gate and `TEST-1.2` mandates unit, integration, and e2e tests; `CLAUDE.md` "Definition of done" makes the coverage gate part of completeness. Without a harness, the security (066), privacy (067), and engine (068) suites have nowhere to run and no enforcement exists. Test tooling is itself a dependency surface and MUST be minimal and vetted (`SEC-9.1`).
- **Design**: Per `DESIGN.md`, the harness has no end-user UI; it produces developer-facing reports. It MUST surface coverage and pass/fail clearly in CI output without leaking secrets or PII into logs (`SEC-8.2`, `NFR-1.3`).

## Scope
- **Applies To**: Both
- **Components**: Backend test runner (e.g. pytest) over the Flask API/scheduler/worker; frontend test runner (e.g. Vitest/Jest + Testing Library) and an e2e driver (e.g. Playwright) over the React SPA; coverage tooling; CI integration (003).
- **Actors**: Developers and CI (no production runtime actor).
- **Data Classification**: Internal (test fixtures MUST NOT embed real Restricted/PII data; synthetic data only).

## Security Context
- **Defense Layer**: Architecture (verification scaffold enabling all downstream security/privacy controls to be tested and enforced).
- **Threat(s) Addressed**: Untested security/privacy regressions reaching production (STRIDE: Tampering, Repudiation via undetected behavioral drift); supply-chain risk from unvetted test dependencies (`SEC-9.1`).
- **Trust Boundary**: CI/CD pipeline boundary — the harness is the enforcement point that blocks merge of unverified code (issue 003).
- **Zero Trust Consideration**: Coverage and pass/fail are computed by the pipeline, not asserted by the author; an indeterminate or errored run MUST fail closed (block merge), never pass by default.

## Standards Alignment
- **OWASP ASVS**: V1.x (secure SDLC / verification process)
- **OWASP AISVS**: n/a (no AI component)
- **NIST SP 800-53**: SA-11 (developer testing and evaluation), CA-2 (assessments)
- **NIST SP 800-207**: n/a
- **Regulatory**: n/a
- **Other**: `TEST-1.1`, `TEST-1.2`, `TEST-1.6`, `SEC-9.1`

## Acceptance Criteria
[Each criterion MUST be independently testable.]

1. **AC-01**: Given the repository, when a developer runs the documented backend and frontend test commands, then unit, integration, and e2e suites all execute and report results (`TEST-1.2`).
2. **AC-02**: Given a CI run, when total statement coverage is computed, then a result below 80% fails the build as a blocking gate. *(verbatim `TEST-1.1`: coverage MUST be at least 80 percent of statements, enforced as a CI gate.)*
3. **AC-03 (negative)**: Given a PR that drops coverage below 80%, when CI runs, then merge is blocked and the failure is reported; the build does not pass on an errored or skipped coverage step (fail closed).
4. **AC-04 (negative)**: Given a test fixture, when reviewed, then it contains no real PII/Restricted data and no committed secrets (`SEC-3.2`, `SEC-8.2`).
5. **AC-05**: Given a newly introduced test dependency, when added, then it is vetted per `SEC-9.1` (CVE history, maintenance, transitive footprint) and pinned with integrity verification (`SEC-9.3`).

## Failure Behavior
- **On Invalid Input**: n/a (developer tooling). A malformed test config fails the CI step, not silently skipped.
- **On System Error**: Fail closed — an errored, timed-out, or partially-run suite blocks merge rather than passing.
- **Alerting**: CI surfaces the failing suite/coverage delta on the PR; persistent flakiness raises a developer-experience signal.

## Test Strategy
- **Unit Tests**: Smoke tests proving each layer's runner is wired (a trivial backend unit test, a frontend component test, and an e2e happy-path) and that coverage is collected from each.
- **Integration Tests**: A backend integration test exercising a request through the Flask app, and a frontend integration test rendering a component against a mocked API.
- **Security Tests**: Verify the coverage gate actually blocks (inject a deliberately uncovered branch and confirm CI fails); confirm fixtures contain no secrets (secret-scan over the test tree).
- **Compliance Tests**: CI log shows the coverage percentage and gate decision as audit evidence for the Definition of Done.
- **Coverage Target**: The harness establishes the ≥80% statement gate project-wide; this issue's own glue code aims ≥80% branch coverage.

## Dependencies
- **Upstream**: 001 (repo scaffolding), 003 (CI pipeline — gate is wired here), 054 (React SPA scaffold, referenced by 055).
- **Downstream**: 066 (security test suite), 067 (privacy test suite), 068 (engine test suite) all run on this harness; every implementation issue relies on it for its Definition-of-Done coverage gate.
- **External**: Test-runner and coverage libraries (vetted per `SEC-9.1`); CI provider (per 003).

## Implementation Notes
- **Constraints**: Backend likely pytest + coverage; frontend a single chosen runner plus one e2e driver — keep the tool count minimal (`SEC-9.1`). Coverage is statement coverage for the `TEST-1.1` gate; branch coverage targets remain per-module. Concrete CI provider follows issue 003.
- **Anti-Patterns**: MUST NOT exclude security/privacy/engine modules from coverage to inflate the number; MUST NOT let the coverage step pass on error (fail closed); MUST NOT embed real PII or secrets in fixtures; MUST NOT add heavyweight or unmaintained test dependencies without `SEC-9.1` vetting.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Straightforward, well-trodden tooling/config work (test runners, coverage gating, CI glue) where broad ecosystem familiarity is the main asset and no novel adversarial reasoning is required. Human review confirms the gate truly blocks and fixtures are PII-free before merge.
