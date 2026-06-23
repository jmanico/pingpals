# Pingpals: SECURITY.md

**Project:** Pingpals (personal relationship cadence and reminder system)
**Document:** SECURITY.md — Secure-Coding Baseline
**Version:** 0.1.0
**Status:** Provisional (bootstrap — no implementation exists yet)
**Conformance:** The keywords MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are interpreted per RFC 2119 and RFC 8174 when used in all capitals.
**Companion documents:** [REQUIREMENTS.md](./REQUIREMENTS.md) (what the system must do), [ARCHITECTURE.md](./ARCHITECTURE.md) (how it is built), [DESIGN.md](./DESIGN.md) (look and feel).
**Primary references:** OWASP Top 10 Proactive Controls, OWASP Cheat Sheet Series, OWASP API Security Top 10, OWASP REST Security Cheat Sheet, OWASP AISVS, and the standards already anchored in REQUIREMENTS.md §13 (RFC 9700, RFC 9068, NIST SP 800-207, NIST SP 800-53 Rev. 5, GDPR, FIPS 203, TLS 1.3).

> Secure-coding contract for all code in this repository. **REQUIREMENTS.md is the source of
> truth; on any conflict, REQUIREMENTS.md wins.** Rules paraphrase their sources — consult the
> cited tag/reference for edge cases.

---

## How To Use This File

- Every rule is a default-deny invariant: if you cannot satisfy it, fail closed rather than ship the weaker path.
- Each rule is tagged with the requirement it compresses or the standard it derives from; tags are the lookup key into REQUIREMENTS.md.
- For undecided stack choices, keep `TO BE DECIDED` and raise the open input rather than inventing infrastructure.

---

## Required Security Inputs

What is **fixed** today and therefore binding on all code. The stack identity (Flask/REST,
React 19 client-only, Docker) is owned by ARCHITECTURE.md; the security-relevant qualifiers below
are authored here:

- **Backend:** Flask/REST stack (ARCHITECTURE.md) — stateless behind cookie sessions, **TLS 1.3 only**.
- **Frontend:** React 19 client-only stack (ARCHITECTURE.md) — Zod validation, **strict CSP**.
- **Auth:** OIDC (Google) SSO + **WebAuthn/passkey** + **MFA**; no password-only path. OAuth
  Authorization Code + PKCE (S256) for all providers (`SEC-1.x`, `INT-1.x`).
- **Posture:** **Zero Trust** (NIST SP 800-207), fail-closed by default, per-request authorization,
  strict per-user tenant isolation, encryption at rest, crypto-agility (REQUIREMENTS.md §7–§8).
- **Privacy:** **GDPR is in play** — the system processes personal data of third-party data subjects
  (the contacts) who are not users. Consent, DSR, erasure cascade, retention, and a DPIA before
  launch are mandatory (REQUIREMENTS.md §7).
- **Packaging:** Docker container image (official slim base, digest-pinned, non-root), cloud-portable (ARCHITECTURE.md).
- **Datastore:** PostgreSQL (behind a repository interface), also backing server-side revocable sessions (`SEC-1.3`).
- **Push:** standard Web Push with the application's own VAPID keys + RFC 8291 message-level payload encryption; fail closed (no push) if message-level protection is unavailable (`FR-5.6`, `FR-6.5`).
- **Crypto / PQ posture:** migration-ready classical baseline (TLS 1.3 + crypto-agility + key rotation); no post-quantum algorithm committed, adoptable later without caller changes (`SEC-5.3`, `SEC-5.4`).
- **CI:** GitHub Actions running the `TEST-1.6` gate set via a provider-agnostic, scriptable definition (`SEC-9.2`).

Remaining infrastructure decisions (queue/broker, KMS vendor, transactional email provider, SMS
provider, audit-chain external anchor store, hosting/region/residency, orchestration) are owned by
ARCHITECTURE.md and remain `TO BE DECIDED`;
until resolved, code MUST keep the choice behind an interface and default to the most restrictive
option.

---

## Provisional Security Rules

### 1. HTTP boundary

- All traffic MUST use **TLS 1.3**; plaintext transport MUST be rejected, not redirected silently
  (`SEC-5.1`).
- A **strict Content Security Policy** MUST be enforced: no inline script, no inline event handlers,
  no `eval`, no `data:`/wildcard script sources (`FE-1.4`).
- Send hardening headers by default: `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`,
  `Referrer-Policy: no-referrer` (or stricter), and a restrictive `Permissions-Policy`.
- External scripts and web fonts MUST use **Subresource Integrity**, or be self-hosted to satisfy the
  CSP (`FE-1.8`, DESIGN §4.1).
- REST endpoints MUST set correct `Content-Type`, MUST NOT reflect `Origin` blindly, and MUST use a
  narrow, explicit CORS allowlist — never `Access-Control-Allow-Origin: *` for credentialed routes
  (OWASP REST / API Security Top 10).
- Return least-information error responses; never leak stack traces, framework banners, or internal
  hostnames to clients (`NFR-1.3`).

### 2. Authentication & session

- Use OIDC (Google) SSO + **WebAuthn/passkeys** with **MFA**; a password-only path MUST NOT exist
  (`SEC-1.1`). Prefer phishing-resistant factors.
- Session tokens MUST live in **HttpOnly, Secure, SameSite** cookies. Session identifiers and bearer
  tokens MUST NOT be placed in `localStorage`, `sessionStorage`, or any script-accessible store
  (`SEC-1.2`, `INT-1.6`).
- Sessions MUST have **idle and absolute** lifetimes and MUST be **server-revocable** (`SEC-1.3`).
- All OAuth flows MUST use **Authorization Code + PKCE (S256)**; the implicit and ROPC grants MUST
  NOT be used (`INT-1.1`).
- Redirect URIs MUST be matched by **exact string comparison** against a preregistered allowlist
  (`INT-1.2`). The authorization response MUST validate `state` (CSRF) and `iss` (mix-up) (`INT-1.3`).
- Access tokens MUST be short-lived; refresh tokens MUST be **rotated on use** with replay detection
  that revokes the whole token family on reuse (`INT-1.4`).
- Tokens MUST NOT appear in URLs, logs, browser history, or client-side storage (`INT-1.6`).
- Where an integration returns an OIDC ID token, the token MUST be fully validated before any session
  is established: signature against the provider JWKS, plus `iss`, `aud`, `exp`, `iat`, and a
  single-use `nonce` bound to the authorization request. Any failure fails closed — no session, no
  cookie. The account MUST be keyed on the immutable `sub` (scoped to `iss`), never on a mutable email
  (`INT-1.8`, `INT-1.9`).
- WebAuthn ceremonies MUST be verified server-side and MUST fail closed (reject, never downgrade) on
  any failed check: the assertion's relying-party ID and `origin` MUST exactly match the registered
  values; the `challenge` MUST be a fresh, server-generated, single-use value bound to the in-flight
  ceremony and consumed on use; user verification (UV) MUST be asserted for the factor to count as
  phishing-resistant MFA; and the signature counter MUST be monotonic, with a non-increasing counter
  rejected as a cloned or replayed authenticator. Registration MUST occur within an already-
  authenticated session and MUST bind the credential to the immutable user id; an assertion that does
  not resolve to exactly one registered credential for the owning user MUST be denied (`SEC-1.1`,
  ARCH Rule 3). Verification: an assertion with a mismatched origin/RP ID, a stale or reused
  challenge, an absent UV flag, or a non-incrementing signature counter is rejected and creates no
  session.
- A fresh, unpredictable session identifier MUST be issued on every privilege transition — successful
  authentication, completion of MFA step-up, and the OIDC/OAuth callback that promotes an anonymous
  session — and any pre-authentication or prior session MUST be invalidated server-side at that
  moment, to prevent session fixation. If a fresh identifier cannot be guaranteed at the transition,
  the request MUST fail closed and the session MUST be denied rather than reused (`SEC-1.2`,
  `SEC-1.3`). Verification: a session identifier captured before authentication is never valid as an
  authenticated session after the same browser logs in.
- OAuth transaction state (the `state`, PKCE `code_verifier`, `nonce`, and expected `iss`) MUST be
  single-use and short-lived: it is consumed and deleted on the first matching callback, expires
  within a few minutes if no callback arrives, and a successful or expired entry MUST NOT be reusable.
  The store of outstanding pending transactions MUST be bounded; when the bound is reached the system
  MUST fail closed by rejecting new authorization initiations rather than growing without limit, so
  that initiating many never-completed authorization requests cannot exhaust storage. This complements
  `SEC-6.1` rate-limiting of authentication and callback endpoints (`INT-1.3`, `SEC-6.1`).
  Verification: a `state`/PKCE entry replayed after first use or after expiry is rejected, and pending
  entries are evicted on expiry.
- Each integration adapter MUST declare a pinned least-privilege scope set, and the authorization
  request MUST be built from that declaration and verified against it at request time; a flow
  requesting any scope outside the adapter's declared set MUST fail closed and MUST NOT proceed
  (`FR-1.5`, `INT-1.7`, `INT-4.1`, `INT-2.2`). Any broadening of an existing integration's authority
  (for example read to write/send), including via incremental or re-consent authorization, MUST
  require a new explicit, recorded user consent capturing the new scope (`PRIV-1.2`); absent that
  consent the broadened request MUST be denied.

### 3. Authorization & tenant isolation

- Every request MUST be **authorized per-request** against the authenticated user; no trust from
  prior auth or network position (`SEC-2.1`, ARCH Dependency Rule 1).
- **All data access MUST be user-scoped.** Every repository/query MUST carry the owning user as a
  non-optional constraint; no code path may read or write across users (`SEC-2.2`, ARCH Rule 4).
- Authorization decisions MUST **fail closed**: an indeterminate or errored policy decision MUST deny
  (`SEC-2.3`, ARCH Rule 3).
- The React client MUST NOT make authorization or data-scoping decisions; it presents what the API
  returns. All security invariants are enforced server-side (ARCH Rule 1).
- Enforce object- and function-level authorization on **every** endpoint (no BOLA/BFLA); reject
  cross-user object access with not-found/forbidden (`SEC-2.2`, OWASP API Security Top 10).
- **CSRF defense on mutating routes.** Because sessions are cookie-borne (`SEC-1.2`), `SameSite` alone
  is insufficient; every state-changing REST request (`POST`/`PUT`/`PATCH`/`DELETE`) MUST be protected
  against cross-site request forgery by an affirmative control beyond `SameSite` — an anti-CSRF token
  (synchronizer or double-submit) or strict request-time `Origin`/`Sec-Fetch-Site` enforcement against
  an exact-match allowlist. This is distinct from the CORS/`Origin`-reflection rule in §1, which
  governs response policy, not request authenticity. Fail closed: a missing, malformed, or
  unverifiable CSRF signal MUST deny the request (`SEC-2.3`). Verification: a cross-site
  `POST`/`DELETE` to a mutating endpoint (for example contact delete, consent withdrawal, erasure)
  carrying a valid session cookie but no valid CSRF signal is rejected with 403 and performs no write
  (`FR-1.3`, `FR-6.2`, `PRIV-1.6`).
- **Zero Trust applies INSIDE the boundary, not only at the API edge.** The "single trust boundary"
  framing for the API MUST NOT be read as implicit trust of internal east-west traffic: the Scheduler,
  Delivery worker, and any queue consumer MUST NOT trust a peer or a work item on network position
  alone (`SEC-2.1`, NIST SP 800-207). Internal service-to-service calls and queue messages MUST be
  authenticated to their producer (for example mTLS or a signed/MAC'd envelope — concrete mechanism
  follows the chosen queue/transport, `TO BE DECIDED`), and every work item MUST be authorized against
  its asserted owning user before any action, exactly as the API authorizes a request (`SEC-2.1`,
  `SEC-2.2`). An internal message that is unauthenticated, fails integrity/replay checks, or cannot be
  authorized to a valid owning user MUST fail closed — rejected and dead-lettered, never processed
  (`SEC-2.3`, ARCH Dependency Rule 8). This is distinct from external webhook signature verification
  (`SEC-7.1`), which governs inbound third-party callbacks. Verification: a forged or replayed
  internal queue message — well-formed against schema but lacking valid producer authentication, or
  asserting an owning user it is not authorized for — is rejected and never produces a delivery.

### 4. Input validation & output handling

- Every inbound edge — user input, **provider responses**, and **webhook payloads** — MUST be
  validated against an explicit schema and **rejected on failure**. Reject over sanitize; provider
  responses are untrusted until validated (`SEC-4.1`, `FR-1.4`, ARCH Rule 2).
- All output rendered in any web context MUST be **contextually encoded**. Never construct HTML from
  untrusted strings (`SEC-4.2`).
- On the client, all form input and all API response data MUST be validated with **Zod** before use
  (`FE-1.2`).
- Reject unknown fields and **never mass-assign**; bound all input. REST endpoints are JSON only,
  set `Content-Type` explicitly, and never echo unvalidated input into responses
  (OWASP API Security Top 10, REST Security Cheat Sheet).
- **Outreach URLs MUST pass an allowlist scheme validator before reaching any sink.** Allowed:
  `mailto`, `tel`, `sms`, `https` (restricted to the click-to-chat host, e.g. `wa.me`), and the
  Signal scheme. Anything else (e.g. `javascript:`, `data:`) MUST resolve to the safe fallback `"#"`.
  No URL reaches a DOM `href`/`src` or a reminder payload without passing this validator
  (`FR-6.4`, `SEC-4.3`, `FE-1.3`, ARCH Rule 6). For the `https` scheme the host MUST be matched
  against the click-to-chat allowlist by **exact string comparison** (no suffix/substring/wildcard),
  and contact-derived components MUST be percent-encoded and unable to alter the scheme, host, or
  authority, so a lookalike like `wa.me.evil.example` is rejected (`FR-6.4`).
- Every schema MUST set explicit upper bounds for each field — maximum string length,
  array/collection cardinality, and numeric range — and unbounded or open-ended fields MUST NOT be
  accepted. Independently, the API MUST enforce a hard maximum request-body size at the HTTP boundary,
  rejecting an oversized request with 413 before deserialization and without buffering the full
  payload into application memory. Bounds fail closed: an over-limit field or body is rejected, never
  truncated or coerced (reject over sanitize) (`FR-1.4`, `SEC-4.1`; DoS/abuse-prevention intent of
  `SEC-6.x`). Verification: a request whose body exceeds the size cap is rejected before any business
  logic runs, and a field exceeding its declared maximum length or cardinality is rejected with a
  field-level error and no partial write.
- Validation patterns MUST be safe against catastrophic backtracking (ReDoS): use linear-time
  matching, anchored patterns with bounded quantifiers, or a non-backtracking engine. A length cap
  MUST be applied BEFORE matching, and untrusted input MUST NOT be compiled into a regex. Validation
  MUST fail closed under resource pressure — a per-request validation time/size budget that is
  exceeded rejects the input rather than blocking the worker (`FR-1.4`, `SEC-4.1`, `SEC-6.x`).
  Verification: a fuzz/complexity test confirms no validator (phone, email, outreach-URL allowlist,
  category name) exceeds a bounded CPU time on adversarial input.

### 5. Secret & key handling

- OAuth tokens and provider credentials MUST be **encrypted at rest** using keys held in a managed
  key store; application code MUST NOT hold raw key material (`SEC-3.1`).
- Restricted data at rest MUST use **AES-256-GCM** or an equivalent authenticated cipher (`SEC-5.2`).
- Secrets MUST NOT be committed to source control; a **secret-scanning gate MUST run in CI**
  (`SEC-3.2`). Secrets MUST NOT be baked into Docker images or build args.
- Tokens MUST be **revoked and purged** on integration disconnect and on account erasure (`SEC-3.3`).
- Crypto MUST be **agile**: algorithms and key references are configurable and rotatable without
  changing callers; maintain a cryptographic inventory (`SEC-5.3`, `SEC-5.5`).
- Secrets and tokens flow **one way**, into the encrypted-at-rest / KMS layer only — never to the
  client, URLs, logs, or audit entries (ARCH Rule 5).
- Backups, snapshots, and any other copies of Restricted data MUST be encrypted with the same
  authenticated cipher and managed keys as primary storage, MUST NOT store decryption keys alongside
  the ciphertext, and are within the erasure/retention and breach scope (`SEC-5.6`, `PRIV-1.6`,
  `PRIV-1.14`). Until the backup mechanism is chosen, default to encrypted, key-separated backups
  (fail closed).
- **Decrypt authority MUST be least-privilege, purpose-scoped, and partitioned per adapter, and MUST
  fail closed.** The right to invoke the key store's decrypt/unwrap operation is itself a sensitive
  grant: holding it yields plaintext even though raw key material never leaves the KMS. Each backend
  component MUST be granted decrypt/unwrap only for the specific class of Restricted data it must
  process, and each integration adapter MUST be able to decrypt and use only its own provider's
  token(s); the decrypt capability MUST be scoped so it cannot resolve another adapter's token
  reference or another data class. There MUST NOT be a single application-wide decrypt role, and any
  principal without an explicit grant MUST be denied (`SEC-3.1`, `SEC-2.1`, `INT-1.7`, ARCH Rule 7,
  NIST SP 800-207). Per-user scoping of all token access (`SEC-2.2`) applies unchanged. While the KMS
  vendor is `TO BE DECIDED`, this scoping MUST be expressed behind the key-store interface and default
  to deny. Every decrypt/unwrap invocation, and every denial, MUST be recorded in the tamper-evident
  audit log, attributing the calling component and purpose and excluding the plaintext (`SEC-8.1`,
  `SEC-8.2`). Verification: a component lacking the grant for a data class, or an adapter attempting to
  decrypt a sibling adapter's token reference, receives a denied response (not plaintext) and an audit
  entry records the denial, and no single role can decrypt every Restricted data class.

### 6. Logging & error handling

- Produce **tamper-evident** audit logs (append-only or hash-chained) for authentication events,
  authorization denials, integration token use, DSR actions, and deletions (`SEC-8.1`).
- Audit and operational logs MUST NOT contain secrets, tokens, message content, or unnecessary
  personal data; PII in logs is minimized and retention-bound (`SEC-8.2`, `NFR-1.3`).
- The audit trail (`SEC-8.1`) MUST cover, at minimum: authentication, authorization denials,
  integration token use, consent grant and withdrawal, rectification, DSR actions, and deletions, each
  with the acting principal, affected object, and a **server-authoritative** timestamp (client time
  MUST NOT be trusted); the audit write shares the mutation's commit and fails closed (`SEC-8.1`,
  `SEC-8.3`). Retention MUST NOT break the append-only/hash chain, and the chain MUST be actively and
  independently verified with an externally-anchored head (`SEC-8.4`, `SEC-8.5`). Erasure MUST leave a
  surviving, PII-free proof-of-action record (`PRIV-1.16`).
- Extend the tamper-evident audit trail (`SEC-8.1`) to reminder delivery: each delivery attempt MUST
  produce an append-only/hash-chained audit event capturing the reminder reference, target channel,
  the consent record in force, the outcome (delivered, retried, dead-lettered), and a server-
  authoritative timestamp — sufficient to establish that delivery occurred on a consented channel
  within the allowed window (`FR-6.2`, `FR-3.3`, `NFR-1.2`). This event flow MUST fail closed: a
  delivery attempt whose outcome cannot be recorded MUST be treated as not-delivered
  (failed/dead-lettered), never silently completed (`SEC-2.3`). The event MUST NOT contain message
  content or personal data beyond the minimal reminder/contact reference and is retention-bound
  (`SEC-8.2`, `FR-5.4`).
- User-facing errors stay gentle and non-blaming (DESIGN §6) but MUST NOT soften a validation
  failure into ambiguity (`FR-1.4`) nor leak internal detail.

### 7. Rate limiting, abuse & webhooks

- **Rate limit** authentication, OAuth callback, DSR, and reminder-delivery endpoints (`SEC-6.1`).
- The scheduler MUST **cap reminders per user per window** to prevent runaway delivery / notification
  flooding (`SEC-6.2`). Reminder generation MUST be **idempotent** — safe to re-run, no duplicates
  for one due event (`FR-5.2`, ARCH Rule 8).
- All inbound webhooks (SMS, WhatsApp, email provider) MUST **verify provider signatures** and reject
  unsigned/invalid requests, with replay mitigation via timestamp or nonce (`SEC-7.1`).

### 8. Deployment & CI/CD safety

- Third-party dependencies MUST be **minimized and vetted** (CVE history, maintenance, transitive
  footprint) before introduction (`SEC-9.1`, ARCH Rule 10).
- CI MUST run the full **TEST-1.6** gate set — **SAST, SCA, secret-scanning, dependency checks** —
  and MUST **block merge** on failure or newly introduced high-severity findings (`TEST-1.6` is
  canonical; `SEC-9.2` is a subset).
- Generate an **SBOM**; pin dependency versions with **integrity verification** (`SEC-9.3`).
- **Docker image hardening:** run as a **non-root** user, use a minimal/pinned base image, install no
  build toolchain into the runtime layer, bake in no secrets, and keep the image free of debug
  servers.
- **Flask hardening:** `debug=False` in any non-dev build (never expose the Werkzeug debugger/PIN);
  set a strong, secret `SECRET_KEY` from the secret store (never hard-coded), rotate per `SEC-3.x`;
  rely on Jinja autoescaping (`SEC-4.2`).
- **Code quality (CI gate):** keep low cyclomatic/cognitive complexity and clear separation of
  concerns (isolate I/O, validation, and business logic); maintain ≥80% statement coverage
  (`TEST-1.1`).
- Cloud, region, orchestrator, KMS vendor, queue/broker, and the email/SMS providers remain
  `TO BE DECIDED` (ARCHITECTURE.md); until chosen, keep them behind interfaces and default to least
  privilege and least exposure. (Resolved: PostgreSQL datastore, Web Push + VAPID/RFC 8291, GitHub
  Actions CI, CycloneDX SBOM, digest-pinned non-root slim base image.)

### 9. GDPR & privacy-by-default

- Document a **lawful basis** for processing contact personal data (expected: legitimate interests,
  Art. 6(1)(f), with a documented LIA); account data under contract, Art. 6(1)(b) (`PRIV-1.1`).
- Record **explicit, granular, withdrawable consent** per notification channel and per optional
  processing, capturing timestamp, scope, and notice version (`PRIV-1.2`). Missing channel consent
  **fails closed** — no delivery (`FR-6.2`).
- Implement **data subject rights**: access & portability, rectification, erasure, restriction,
  objection (`PRIV-1.3`). Export MUST be machine-readable and complete (`PRIV-1.5`).
- **Erasure MUST be a hard-delete cascade** across contacts, reminders, outreach history, derived
  detection data, and provider tokens; no orphaned personal data may remain (`PRIV-1.6`, `FR-1.3`,
  ARCH Rule 9).
- Enforce **data minimization** (only approved fields/classes), **purpose limitation**, and
  **storage limitation** via an automated retention job (`PRIV-1.7`, `PRIV-1.8`, `PRIV-1.9`).
- **Privacy by default:** integrations off, automatic detection off, minimum scopes (`PRIV-1.13`).
- Assess a personal-data breach and, where required, notify within **72 hours** (`PRIV-1.14`).

### 10. Future AI controls (if LLM features are added)

- The LLM MUST NOT have authority to send messages or mutate data; it produces **draft text only**
  for user review (REQUIREMENTS.md §12).
- Treat all contact data and external content as untrusted; apply **prompt-injection screening** on
  inputs.
- Model output MUST be validated and encoded before rendering, MUST NOT be executed, and MUST pass
  the `FR-6.4` URL allowlist before becoming any link.
- Any tool exposed to the model MUST be least-privilege, schema-validated, and fail closed (OWASP
  AISVS).

---

## Standards Traceability

| Rule group | External references | Project anchors (REQUIREMENTS.md §13) |
| --- | --- | --- |
| HTTP boundary, input/output | OWASP Top 10 Proactive Controls, OWASP Cheat Sheet Series | `SEC-4.x`, `SEC-5.1`, `FE-1.x`, OWASP ASVS |
| API security | OWASP API Security Top 10, OWASP REST Security Cheat Sheet | `SEC-2.x`, `SEC-6.1` |
| AuthN / session / OAuth | OWASP Authentication & Session Mgmt cheat sheets, WebAuthn | `SEC-1.x`, `INT-1.x` → RFC 9700, RFC 9068 |
| AuthZ / tenant isolation | OWASP Proactive Controls (access control) | `SEC-2.x` → NIST SP 800-207 |
| Secrets / crypto | OWASP Cheat Sheet Series (secrets, cryptographic storage) | `SEC-3.x`, `SEC-5.x` → FIPS 203, RFC 8446 |
| Logging / audit | OWASP Logging Cheat Sheet | `SEC-8.x` → NIST SP 800-53 (AU) |
| Dependencies / CI-CD | OWASP CI/CD Security, OWASP Dependency guidance | `SEC-9.x`, `TEST-1.6` |
| Privacy / GDPR | — | `PRIV-1.x` → GDPR Arts. 5, 6, 13–21, 25, 30, 32–35 |
| Future AI | OWASP AISVS | REQUIREMENTS.md §12 |

---

## Open Security Items

Open items are of record in REQUIREMENTS.md §14. Still open/deferred: the remaining infrastructure
`TO BE DECIDED` inputs — KMS vendor, queue/broker, transactional email provider, SMS provider,
audit-chain external anchor store, orchestrator (ARCHITECTURE.md); DPIA + Legitimate Interests
Assessment and qualified-advisor sign-off before launch (`PRIV-1.11`, `PRIV-1.1`); future
cross-user/identity-verified direct third-party erasure intake beyond the MVP controller-mediated
model (`PRIV-1.4`); and hosting region / data residency and cross-border transfer mechanism
(`PRIV-1.12`), whose deferral blocks finalizing processor DPAs. The operational alerting
destination is deferred behind an alerting abstraction.
