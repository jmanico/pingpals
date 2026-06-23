#!/usr/bin/env bash
# Create the Pingpals epic + all sub-issues from the body files in this directory.
#
#   bash issues/create-issues.sh --dry-run   # print the gh commands, create nothing
#   bash issues/create-issues.sh             # create sub-issues, then the epic with a
#                                            # task list linking the real issue numbers
#
# Re-runnable: it does NOT dedupe, so run once. Use --dry-run first to review.
# Requires: gh (authenticated), run from the repo root or anywhere (uses --repo).
set -euo pipefail

REPO="${REPO:-jmanico/pingpals}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY=0
[[ "${1:-}" == "--dry-run" ]] && DRY=1

# Manifest: one row per sub-issue, in creation order.
#   file | comma,separated,labels | TITLE
# Labels must already exist (run labels.sh first).
MANIFEST=$(cat <<'ROWS'
001-repo-scaffolding.md|area:foundation,priority:critical|[FOUNDATION] Repo & module scaffolding (Flask API + React SPA, client-only)
002-docker-hardening.md|area:foundation,security,priority:high|[FOUNDATION] Docker image hardening (non-root, pinned minimal base, no secrets)
003-ci-pipeline.md|area:foundation,security,priority:critical|[FOUNDATION] CI pipeline: SAST + SCA + secret-scan + dep-check + >=80% coverage gate
004-sbom-dep-pinning.md|area:foundation,security,priority:high|[FOUNDATION] SBOM generation + pinned dependencies with integrity verification
005-design-tokens.md|area:foundation,area:frontend,priority:high|[FOUNDATION] Design-token source file (palette, type scale, spacing, radii)
006-crypto-inventory.md|area:foundation,security,priority:medium|[FOUNDATION] Cryptographic inventory + crypto-agility config scaffold
007-flask-skeleton.md|area:backend,security,priority:critical|[BACKEND] Flask app skeleton + hardened config (debug off, SECRET_KEY from store)
008-http-boundary-headers-csp.md|area:backend,security,priority:critical|[BACKEND] HTTP boundary: TLS 1.3 enforce, strict CSP, security headers, CORS allowlist
009-input-validation-framework.md|area:backend,security,priority:critical|[BACKEND] Request-body size cap + bounded, ReDoS-safe schema-validation framework
010-persistence-user-scoping.md|area:backend,security,priority:critical|[BACKEND] Per-user-scoped persistence/repository layer + core entity migrations
011-kms-encryption-at-rest.md|area:backend,security,priority:critical|[BACKEND] KMS interface + AES-256-GCM at-rest envelope, partitioned decrypt authority
012-audit-log-subsystem.md|area:backend,security,priority:critical|[BACKEND] Tamper-evident audit log (hash-chain, server-time, external anchor, verifier)
013-rate-limiting-concurrency.md|area:backend,security,priority:high|[BACKEND] Per-user baseline rate-limit + per-op concurrency caps middleware
014-authorization-decision-point.md|area:backend,security,priority:critical|[BACKEND] Per-request authorization decision point (fail-closed, object+function level)
015-csrf-protection.md|area:backend,security,priority:critical|[BACKEND] CSRF protection for all mutating routes
016-internal-message-authn.md|area:backend,security,priority:high|[BACKEND] Internal east-west authn: signed work-item envelope + per-item authz
017-oidc-sso-initiation.md|area:auth,security,priority:critical|[AUTH] OIDC Google SSO initiation: Authz-Code+PKCE(S256) + state/nonce txn store
018-oidc-idtoken-validation.md|area:auth,security,priority:critical|[AUTH] OIDC ID-token full validation + account binding on immutable sub/iss
019-session-management.md|area:auth,security,priority:critical|[AUTH] Session mgmt: HttpOnly/Secure/SameSite cookies, lifetimes, fixation rotation
020-webauthn-registration.md|area:auth,security,priority:high|[AUTH] WebAuthn/passkey registration ceremony
021-webauthn-assertion-mfa.md|area:auth,security,priority:high|[AUTH] WebAuthn/passkey assertion + MFA step-up
022-oauth-provider-adapter.md|area:auth,security,priority:high|[AUTH] Generic OAuth provider adapter: scope-pinning + refresh rotation w/ replay revoke
023-account-linking-reauth.md|area:auth,security,priority:high|[AUTH] Provider-identity/account linking with fresh re-auth + session binding
024-contact-crud.md|area:contacts,priority:high|[CONTACTS] Contact CRUD API + schema validation (reject-over-sanitize, no mass-assign)
025-contact-deletion-cascade.md|area:contacts,privacy,priority:high|[CONTACTS] Contact deletion cascade (single transaction, no orphans)
026-category-crud.md|area:contacts,priority:high|[CONTACTS] Category CRUD + default cadences + reassign-on-delete fail-closed
027-cadence-config.md|area:contacts,priority:high|[CONTACTS] Cadence config + quiet-hours/timezone fail-closed
028-last-contact-logging.md|area:contacts,priority:high|[CONTACTS] Last-contact event logging + cadence-clock reset (server vs asserted time)
029-resource-quotas.md|area:contacts,security,priority:medium|[CONTACTS] Per-user resource quotas (contacts, categories, import batch size)
030-google-people-import.md|area:contacts,security,priority:medium|[CONTACTS] Google People contact import (least scope, paginated, dedupe)
031-scheduler-cadence-evaluation.md|area:engine,priority:critical|[ENGINE] Scheduler cadence evaluation + idempotent reminder generation
032-reminder-generation-cap.md|area:engine,security,priority:high|[ENGINE] Reminder per-user-per-window generation cap
033-reminder-actions.md|area:engine,priority:high|[ENGINE] Reminder actions: snooze / dismiss / mark-contacted
034-channel-consent-enforcement.md|area:engine,privacy,security,priority:critical|[ENGINE] Channel-consent enforcement at evaluation + delivery (fail-closed)
035-delivery-worker-owner-verification.md|area:delivery,security,priority:critical|[DELIVERY] Delivery worker: per-reminder owner re-verify + endpoint-ownership check
036-reminder-payload-confidentiality.md|area:delivery,security,privacy,priority:high|[DELIVERY] Minimal/opaque reminder payload + third-party-channel confidentiality
037-delivery-endpoint-lifecycle.md|area:delivery,security,priority:high|[DELIVERY] Delivery-endpoint registration & lifecycle (proof-of-control, revoke)
038-email-delivery-adapter.md|area:delivery,priority:high|[DELIVERY] Email delivery adapter (transactional provider, authenticated API)
039-email-anti-spoofing.md|area:delivery,security,priority:high|[DELIVERY] Email anti-spoofing: SPF + DKIM + DMARC p=reject alignment
040-web-push-adapter.md|area:delivery,security,priority:high|[DELIVERY] Web-push adapter: VAPID auth + RFC 8291 message encryption
041-delivery-retry-circuit-breaker.md|area:delivery,priority:high|[DELIVERY] Delivery retry/backoff + per-channel circuit breaker + bounded DLQ
042-delivery-audit-events.md|area:delivery,security,priority:medium|[DELIVERY] Delivery audit events (channel, consent-in-force, outcome, server time)
043-outreach-link-service.md|area:delivery,security,priority:critical|[DELIVERY] Outreach-link service: allowlist scheme+host validator, fallback #
044-notification-preferences.md|area:delivery,priority:medium|[DELIVERY] Notification preferences: channel order, per-category override, global pause
045-consent-records-store.md|area:privacy,security,compliance,priority:critical|[PRIVACY] Consent records: append-only immutable event store + effective-state derivation
046-data-export.md|area:privacy,compliance,priority:high|[PRIVACY] Data export: machine-readable, complete, round-trippable
047-export-artifact-access-control.md|area:privacy,security,priority:high|[PRIVACY] Export artifact access control (owner session / single-use token, expiry)
048-erasure-cascade.md|area:privacy,security,compliance,priority:critical|[PRIVACY] Erasure: hard-delete cascade across all stores + provider tokens
049-proof-of-erasure.md|area:privacy,security,compliance,priority:high|[PRIVACY] Surviving PII-free, tamper-evident proof-of-erasure record
050-dsr-endpoints.md|area:privacy,compliance,priority:high|[PRIVACY] DSR endpoints: access, rectification, restriction, objection, portability
051-retention-job.md|area:privacy,compliance,priority:high|[PRIVACY] Automated retention job (PII + accountability retention; chain re-anchor)
052-privacy-by-default.md|area:privacy,priority:medium|[PRIVACY] Privacy-by-default config + free-text notes Article-9 entry guard
053-ropa-dpia-lia-docs.md|area:privacy,compliance,documentation,priority:high|[PRIVACY] RoPA + DPIA + LIA documentation artifacts
054-react-spa-scaffold.md|area:frontend,security,priority:high|[FRONTEND] React 19 SPA scaffold (client-only, strict CSP, SRI, UUID keys)
055-validate-sanitize-url.md|area:frontend,security,priority:critical|[FRONTEND] validateAndSanitizeUrl utility + exhaustive scheme/host tests
056-zod-validation-layer.md|area:frontend,security,priority:high|[FRONTEND] Zod validation layer for all form input + API responses
057-api-client.md|area:frontend,security,priority:high|[FRONTEND] API client: cookie session + CSRF header + AbortController fetch pattern
058-auth-ui.md|area:frontend,priority:high|[FRONTEND] Auth UI (Google SSO, passkey register/assert, MFA step-up)
059-contact-management-ui.md|area:frontend,priority:high|[FRONTEND] Contact management UI
060-category-cadence-ui.md|area:frontend,priority:medium|[FRONTEND] Category & cadence UI
061-reminder-card-ui.md|area:frontend,priority:high|[FRONTEND] Reminder list + reminder card (speech-bubble, single outreach action)
062-notification-preferences-ui.md|area:frontend,priority:medium|[FRONTEND] Notification preferences UI
063-privacy-center-ui.md|area:frontend,privacy,priority:medium|[FRONTEND] Consent & privacy center UI (export / erasure / DSR)
064-component-library-a11y.md|area:frontend,priority:high|[FRONTEND] Base component library on tokens + WCAG 2.2 AA pass
065-test-harness-coverage.md|area:testing,priority:high|[TESTING] Test harness + >=80% coverage gate wiring (unit/integration/e2e)
066-security-test-suite.md|area:testing,security,priority:high|[TESTING] Security test suite (isolation, redirect match, URL scheme, token, webhook)
067-privacy-test-suite.md|area:testing,privacy,priority:high|[TESTING] Privacy test suite (erasure, export, consent fail-closed, retention)
068-engine-test-suite.md|area:testing,priority:high|[TESTING] Reminder-engine test suite (idempotency, cadence boundaries, quiet hours)
069-decision-database-engine.md|decision,priority:critical|[DECISION] Database engine + schema realization
070-decision-queue-broker.md|decision,priority:high|[DECISION] Durable queue/broker for reminder enqueue/retry/DLQ
071-decision-push-provider.md|decision,priority:high|[DECISION] In-app/push delivery mechanism + provider
072-decision-kms-vendor.md|decision,security,priority:high|[DECISION] Managed KMS vendor
073-decision-hosting-region.md|decision,privacy,priority:high|[DECISION] Hosting cloud / region / data residency
074-decision-post-quantum.md|decision,security,priority:medium|[DECISION] Hybrid post-quantum key exchange support
075-decision-third-party-erasure.md|decision,privacy,compliance,priority:medium|[DECISION] Direct third-party (contact) erasure intake + identity verification
076-later-contact-providers.md|later-phase,priority:medium|[LATER] Additional contact providers (MS Graph, CardDAV, Apple)
077-later-calendar-integration.md|later-phase,priority:medium|[LATER] Calendar integration (meeting-aware cadence) + inbound webhook security
078-later-messaging-channels.md|later-phase,priority:medium|[LATER] SMS / WhatsApp / Signal delivery + webhook signature verification
079-later-mailbox-detection.md|later-phase,privacy,priority:medium|[LATER] Opt-in mailbox-metadata last-contact detection
ROWS
)

declare -a TASKLINES=()

while IFS='|' read -r file labels title; do
  [[ -z "$file" ]] && continue
  body="$DIR/$file"
  if [[ ! -f "$body" ]]; then echo "MISSING body file: $body" >&2; exit 1; fi
  if [[ $DRY -eq 1 ]]; then
    echo "gh issue create --repo $REPO --title \"$title\" --body-file \"$file\" --label \"$labels\""
    TASKLINES+=("- [ ] $title")
  else
    url=$(gh issue create --repo "$REPO" --title "$title" --body-file "$body" --label "$labels")
    num=$(basename "$url")
    echo "created #$num  $title"
    TASKLINES+=("- [ ] #$num $title")
  fi
done <<< "$MANIFEST"

# Build the epic body: EPIC.md with its <!-- TASKLIST --> marker replaced by the
# generated task list. Task lines are passed via a temp file (awk -v cannot hold newlines).
tltmp=$(mktemp)
printf '%s\n' "${TASKLINES[@]}" > "$tltmp"
epictmp=$(mktemp)
awk -v f="$tltmp" '
  /<!-- TASKLIST -->/ { while ((getline line < f) > 0) print line; next }
  { print }
' "$DIR/EPIC.md" > "$epictmp"
rm -f "$tltmp"

if [[ $DRY -eq 1 ]]; then
  echo "---- EPIC body (dry-run, first 45 lines) ----"
  sed -n '1,45p' "$epictmp"
  echo "gh issue create --repo $REPO --title \"[EPIC] Pingpals MVP build\" --body-file <generated> --label epic,priority:critical"
  rm -f "$epictmp"
else
  epic_url=$(gh issue create --repo "$REPO" --title "[EPIC] Pingpals MVP build" --body-file "$epictmp" --label "epic,priority:critical")
  rm -f "$epictmp"
  echo "created EPIC  $epic_url"
fi
