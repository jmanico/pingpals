#!/usr/bin/env bash
# Generate CycloneDX SBOMs for both modules (REQ-FND-004 AC-01, SEC-9.3).
# CycloneDX is the resolved SBOM format (REQUIREMENTS.md §14). Output is a build artifact,
# git-ignored (sbom-*.json) and retained by CI.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT}"

echo "Generating API SBOM (CycloneDX) -> $OUT/sbom-api.json"
( cd "$ROOT/api" && pip-audit --require-hashes --requirement requirements.lock.txt \
    --format cyclonedx-json --output "$OUT/sbom-api.json" )

echo "Generating WEB SBOM (CycloneDX) -> $OUT/sbom-web.json"
( cd "$ROOT/web" && npm sbom --sbom-format cyclonedx > "$OUT/sbom-web.json" )

echo "SBOMs written: sbom-api.json, sbom-web.json"
