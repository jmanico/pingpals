# Testing & coverage harness (REQ-TEST, issue 076)

The test harness enforces the `TEST-1.x` requirements: unit + integration + e2e tests with a
**≥80% statement-coverage gate** (TEST-1.1) and the security/SCA/secret/dep CI gates (TEST-1.6).

## API (Python / pytest)

- **Runner:** `pytest`, configured in `api/pyproject.toml` with `--cov=pingpals_api
  --cov-fail-under=80` — the build fails below 80%.
- **Layers:**
  - *Unit* — per-module suites (e.g. `test_validation.py`, `test_crypto_agility.py`).
  - *Integration / e2e* — `test_integration_app.py` drives the wired `create_app` stack
    (boundary headers, CSRF, rate limit, authz, audit) through the Flask test client.
  - *Requirement suites* mapping to TEST-1.x:
    - `test_security_suite.py` — TEST-1.3 (isolation, redirect exact-match, URL scheme, token
      non-exposure, webhook signature).
    - `test_privacy_suite.py` — TEST-1.4 (erasure cascade, export completeness, consent
      fail-closed, retention expiry).
    - `test_engine_suite.py` — TEST-1.5 (idempotency, cadence boundaries, quiet-hours/timezone
      fail-closed).
- **Run:** `bash scripts/ci-api.sh` (ruff + bandit + pip-audit + pytest+coverage).

## Web (TypeScript / vitest)

- **Runner:** `vitest` (jsdom). Component tests use `@testing-library/react`; a source-guard test
  fails the build on `dangerouslySetInnerHTML` or array-index keys (FE-1.1/1.6).
- **Run:** `bash scripts/ci-web.sh` (tsc + npm audit + vitest).

## CI gate (TEST-1.6)

`.github/workflows/ci.yml` runs SAST (ruff/bandit), SCA (pip-audit/npm audit), secret scanning
(gitleaks), the coverage gate, and SBOM generation, and blocks merge on failure or any newly
introduced high-severity finding. Marking these jobs as **required status checks** on `main`
(branch protection) is what physically blocks merge.
