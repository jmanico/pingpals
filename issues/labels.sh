#!/usr/bin/env bash
# Create / update the Pingpals label taxonomy on the GitHub repo.
# Idempotent: --force updates an existing label instead of erroring.
# Usage: bash issues/labels.sh
set -euo pipefail

REPO="${REPO:-jmanico/pingpals}"

mklabel() {
  local name="$1" color="$2" desc="$3"
  gh label create "$name" --repo "$REPO" --color "$color" --description "$desc" --force
}

# Type / workflow
mklabel "epic"             "6f42c1" "Parent tracking issue for a body of work"
mklabel "decision"         "d4c5f9" "Open infrastructure/process decision; blocks dependents"
mklabel "later-phase"      "c2e0c6" "Out of MVP scope; tracked for a later phase"

# Area
mklabel "area:foundation"  "fef2c0" "Repo scaffolding, tooling, CI, tokens"
mklabel "area:backend"     "0e8a16" "Flask core platform / cross-cutting services"
mklabel "area:auth"        "1d76db" "Authentication, session, OAuth/OIDC, WebAuthn"
mklabel "area:contacts"    "0052cc" "Contacts, categories, cadence, import"
mklabel "area:engine"      "5319e7" "Reminder scheduler / cadence evaluation"
mklabel "area:delivery"    "b60205" "Reminder delivery, channels, outreach links"
mklabel "area:privacy"     "fbca04" "GDPR / DSR / consent / retention"
mklabel "area:frontend"    "e99695" "React 19 SPA"
mklabel "area:testing"     "bfd4f2" "Test suites and coverage gates"

# Classification
mklabel "security"         "b60205" "Security control; subtle error is a vulnerability"
mklabel "privacy"          "fbca04" "Processes personal data / GDPR-relevant"
mklabel "compliance"       "d93f0b" "Regulatory / accountability artifact"

# Priority
mklabel "priority:critical" "b60205" "Blocks the build or a security/privacy invariant"
mklabel "priority:high"     "d93f0b" "Needed for a usable MVP"
mklabel "priority:medium"   "fbca04" "Important but schedulable"

echo "Labels ensured on $REPO."
