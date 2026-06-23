#!/usr/bin/env bash
# CI gates for the React 19 SPA module (REQ-FND-003 / TEST-1.6).
# Fails closed via `set -euo pipefail`.
set -euo pipefail

cd "$(dirname "$0")/../web"

echo "::group::WEB :: install (integrity-verified, lockfile-strict)"
# `npm ci` refuses to run without a lockfile and verifies per-package integrity hashes.
npm ci --no-audit --no-fund
echo "::endgroup::"

echo "::group::WEB :: typecheck (tsc, SAST-adjacent)"
npx tsc --noEmit
echo "::endgroup::"

echo "::group::WEB :: SCA + dependency check (npm audit)"
# High-severity advisories block merge (REQ-FND-003 AC-02).
npm audit --audit-level=high
echo "::endgroup::"

echo "::group::WEB :: tests + coverage (vitest)"
npm run test
echo "::endgroup::"

echo "WEB gates passed."
