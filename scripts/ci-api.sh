#!/usr/bin/env bash
# CI gates for the Flask API module (REQ-FND-003 / TEST-1.6).
# Provider-agnostic: the GitHub Actions workflow is a thin wrapper around this script.
# Fails closed — `set -euo pipefail` makes any gate error abort the whole run (non-zero exit).
set -euo pipefail

cd "$(dirname "$0")/../api"

echo "::group::API :: install (hash-verified, fail closed on mismatch)"
python -m pip install --require-hashes --no-deps -r requirements.lock.txt
python -m pip install --require-hashes --no-deps -r requirements-dev.lock.txt
python -m pip install --no-deps -e .
echo "::endgroup::"

echo "::group::API :: SAST + lint (ruff)"
ruff check src tests
echo "::endgroup::"

echo "::group::API :: SAST (bandit)"
# -ll = report medium+ severity; non-zero exit on findings blocks merge.
bandit -q -r src -ll
echo "::endgroup::"

echo "::group::API :: SCA + dependency integrity (pip-audit)"
# Audits the hash-pinned lock; a known-vuln dependency fails the gate.
pip-audit --require-hashes --requirement requirements.lock.txt
echo "::endgroup::"

echo "::group::API :: tests + >=80% coverage gate (TEST-1.1)"
# --cov-fail-under=80 is configured in pyproject.toml [tool.pytest.ini_options].
python -m pytest
echo "::endgroup::"

echo "API gates passed."
