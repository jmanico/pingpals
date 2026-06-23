# Pingpals: ARCHITECTURE.md

**Project:** Pingpals (personal relationship cadence and reminder system)
**Document:** ARCHITECTURE.md
**Version:** 0.1.0
**Status:** Provisional (bootstrap — no implementation exists yet)
**Companion documents:** [REQUIREMENTS.md](./REQUIREMENTS.md) (what the system must do), [DESIGN.md](./DESIGN.md) (look and feel)

> This is a first-pass intended architecture derived from REQUIREMENTS.md and the explicit human-provided inputs below. The repository currently contains only REQUIREMENTS.md and DESIGN.md; nothing here is reverse-engineered from code. Unknowns are kept visible as `TO BE DECIDED` rather than guessed. REQUIREMENTS.md remains the source of truth; where this document and REQUIREMENTS.md disagree, REQUIREMENTS.md wins.

---

## Required Architecture Inputs

```
Requirements source: REQUIREMENTS.md
System purpose: A single-user relationship-cadence reminder system. Pingpals nudges the
  account owner to maintain contact with people they choose to track, at a per-relationship
  cadence. It never acts on third-party platforms on the user's behalf — it delivers the
  reminder to the user and hands them a one-tap deep link to open their own messaging app.
  (REQUIREMENTS.md §1, §2.3)
System design: Regal/playful "King Ping" brand. Parchment canvas, Royal Purple lead with
  Gold accent, serif display + Inter UI, crown/speech-bubble/mascot motifs. Secure-by-default
  React 19 client; WCAG 2.2 AA. (DESIGN.md §1–§7, NFR-1.4)
Primary use cases: (a) create/import/categorize contacts; (b) set per-category and
  per-contact cadence, quiet hours, timezone; (c) log last-contact events; (d) scheduler
  evaluates cadence and enqueues reminders; (e) deliver reminders to the user (email +
  in-app/push in MVP); (f) one-tap outreach via validated deep links; (g) GDPR consent,
  export, erasure, retention. (REQUIREMENTS.md §5, §2.1)
Target users / actors: User (account owner, sole controller of their data set); Contact
  (third-party data subject, NOT a system user, holds GDPR rights); Scheduler (internal
  service); Integration provider (external OAuth-protected API). (REQUIREMENTS.md §4)
Runtime environment: web application
Server framework: Python Flask
Client framework: ReactJS (React 19, client-only, function components + hooks, no SSR — FE §9)
API style and integration model: REST
Authentication and session model: SSO/OIDC (Google) + Passkey/Password hybrid with MFA.
  No password-only auth (sensitive personal data). WebAuthn/passkeys preferred and phishing
  resistant; MFA required. Sessions in HttpOnly/Secure/SameSite cookies, server-revocable,
  idle + absolute lifetimes. (SEC-1.x)
Data model expectations: Per-user isolated data set. Core entities: User, Contact, Category,
  Cadence (interval days + optional preferred day/send window), Reminder, ConsentRecord,
  ContactEvent (last-contact log), OutreachAction, ProviderToken (encrypted), AuditLogEntry.
  Data classes: Restricted (contact PII, OAuth tokens, consent, audit), Confidential
  (credentials/session), Internal (PII-free aggregate metrics). Strict minimization — only
  fields in §6.4 and classes in §3. (REQUIREMENTS.md §3, §5, §6.4, PRIV-1.7)
Deployment model: Docker container (cloud-portable; runs on many clouds). Specific
  orchestrator/cloud TO BE DECIDED.
Scale expectations: Designed to grow to a large user base ("go viral"). Reminder evaluation
  MUST be horizontally scalable across users; per-user work is independent and shardable.
  (NFR-1.1)
Security expectations: Security is critical. Zero Trust (NIST SP 800-207), fail-closed by
  default, per-request authorization, strict tenant isolation, TLS 1.3, encryption at rest,
  crypto-agility. GDPR is in play (third-party data subjects) — consent, DSR, erasure
  cascade, retention, DPIA before launch. (REQUIREMENTS.md §7, §8)
```

---

## Initial Architecture (Provisional)

A client-only React 19 SPA talking over REST/TLS 1.3 to a Flask API. The API is the single
trust boundary: every request is authorized per-request against the authenticated user and
fails closed. An internal Scheduler evaluates cadence and enqueues reminders to a delivery
worker. All third-party access is least-privilege OAuth. Outreach never leaves the user's
own device — the API only ever returns a validated deep link for the client to open.

**Components (logical, not a file layout):**

- **Web client (React 19 SPA).** Client-only, no SSR. Validates all input and all API
  responses with Zod (FE-1.2). Every `href`/`src` passes `validateAndSanitizeUrl`, returning
  `"#"` on failure (FE-1.3, FR-6.4). Strict CSP, no `dangerouslySetInnerHTML`, no inline
  script/handlers (FE-1.1, FE-1.4). Consumes DESIGN.md tokens; never hard-coded styles.
- **API service (Flask, REST).** Stateless behind cookie sessions. Schema-validates all
  external input and rejects on failure — reject over sanitize (FR-1.4, SEC-4.1). Enforces
  per-request authz and per-user data scoping on every endpoint (SEC-2.x). Contextually
  encodes all output (SEC-4.2). Rate-limits auth/OAuth-callback/DSR/delivery endpoints
  (SEC-6.1).
- **AuthN/Session subsystem.** OIDC (Google) for SSO + WebAuthn/passkeys with MFA;
  no password-only path. Authorization Code + PKCE (S256) for all OAuth; exact redirect-URI
  match; `state` + `iss` validation; refresh-token rotation with replay-family revocation
  (INT-1.x). Tokens never in URLs/logs/script-accessible storage (INT-1.6, SEC-1.2).
- **Scheduler service.** Per-user cadence evaluation: emits a reminder when
  `now − last_contacted ≥ effective_cadence` AND within send window AND channel consent
  present AND no active snooze (FR-5.1). Idempotent generation (FR-5.2). Fails closed on
  unknown timezone (FR-3.3); caps reminders per user per window (SEC-6.2). Horizontally
  scalable by user shard (NFR-1.1).
- **Delivery worker.** Sends to the user via email and in-app/push (MVP). Per-channel
  affirmative consent required; absence fails closed (FR-6.2). Retries + dead-letter
  (NFR-1.2). Payload is minimal: display name, channel, outreach action only — no tokens/PII
  (FR-5.4).
- **Outreach-link service.** Builds deep links (`mailto`, `tel`, `sms`, `https` wa.me,
  Signal) behind an allowlist validator; any other scheme → `"#"` (FR-6.4, SEC-4.3). The
  system never transmits into those platforms.
- **Integration adapters.** Google People (contacts read, least scope) in MVP; transactional
  email provider. Each independently revocable; tokens purged on disconnect/erasure
  (INT-1.7, SEC-3.3). Later: Microsoft Graph, CardDAV, calendar, SMS/WhatsApp/Signal.
- **Privacy/DSR subsystem.** Consent records (timestamp, scope, notice version); machine-
  readable export; hard-delete erasure cascade across contacts/reminders/outreach/derived/
  tokens; automated retention job (PRIV-1.2, 1.5, 1.6, 1.9). Privacy-by-default: integrations
  off, detection off, minimum scopes (PRIV-1.13).
- **Persistence + secret/key management.** Encrypted-at-rest Restricted data (AES-256-GCM or
  equivalent) with keys in a managed key store; app code has no raw key material (SEC-3.1,
  SEC-5.2). Crypto-agile, rotatable (SEC-5.3). Tamper-evident append-only/hash-chained audit
  log, no secrets/PII (SEC-8.x).
- **Packaging.** Docker container image, cloud-portable.

```
[React 19 SPA] --REST/TLS1.3--> [Flask API] --+--> [AuthN/Session: OIDC + passkey/MFA]
      |  validateAndSanitizeUrl on hrefs       |
      |                                         +--> [Scheduler] --> [Delivery worker] --> user (email, push/in-app)
   opens deep link in                          |
   user's own app  <--- outreach link ---------+--> [Outreach-link service (allowlist)]
                                               +--> [Integration adapters: Google People, email] (least-privilege OAuth)
                                               +--> [Privacy/DSR: consent, export, erasure, retention]
                                               +--> [Persistence + KMS + tamper-evident audit log]
```

**Assumptions (to confirm):**

- `[ASSUMPTION]` Scheduler + Delivery worker run as background processes alongside the Flask
  API; whether they share or split container images is a deployment detail, not yet decided.
- `[ASSUMPTION]` Reminder enqueue uses a durable queue between Scheduler and Delivery worker
  (needed for idempotency/retry/dead-letter, FR-5.2/NFR-1.2). Concrete queue is TBD.
- `[ASSUMPTION]` In-app/push delivery uses standard web push; exact mechanism TBD.
- `[ASSUMPTION]` "Many clouds" implies no hard dependency on a single cloud's proprietary
  service in MVP; managed KMS is abstracted behind an interface.

**Explicitly NOT chosen here (no input given):**

- Data store / database engine — `TO BE DECIDED` (only the entities and isolation rules are
  fixed by REQUIREMENTS.md, not the engine).
- Queue/broker, cache, push provider, managed KMS vendor, hosting cloud/region,
  orchestration (k8s vs. plain Docker) — all `TO BE DECIDED`.
- Data residency / cross-border transfer region — `TO BE DECIDED` (open question, §14).

---

## Requirement Traceability

| Architecture component / boundary | Requirement groups |
| --- | --- |
| Web client (React 19 SPA) | FE-1.1–1.8, NFR-1.4, DESIGN.md §7 |
| API service (REST, per-request authz, tenant isolation) | SEC-2.x, SEC-4.x, SEC-6.1, FR-1.4 |
| AuthN/Session (OIDC + passkey/MFA, OAuth baseline) | SEC-1.x, INT-1.x |
| Scheduler | FR-3.x, FR-5.1, FR-5.2, NFR-1.1, SEC-6.2 |
| Delivery worker (email + in-app/push MVP) | FR-6.1, FR-6.2, FR-5.4, FR-7.x, NFR-1.2 |
| Outreach-link service (scheme allowlist) | FR-6.3, FR-6.4, SEC-4.3 |
| Integration adapters (Google People, email) | FR-1.5, INT-2.x, INT-4.x |
| Privacy/DSR subsystem | PRIV-1.x, FR-1.3 |
| Persistence + KMS + audit log | SEC-3.x, SEC-5.x, SEC-8.x, §3 data classification |
| Contact/Category/Cadence data model | FR-1.x, FR-2.x, FR-3.x, FR-4.x |
| Packaging (Docker) | NFR-1.1 (horizontal scale), human-provided deployment input |

**Requirements needing more architecture input (`TO BE DECIDED`):**

- Database engine and schema realization for the data model (§3, §5). — `TO BE DECIDED`
- Durable queue / broker for reminder enqueue, retry, dead-letter (FR-5.2, NFR-1.2). — `TO BE DECIDED`
- In-app/push delivery mechanism and provider (FR-6.1). — `TO BE DECIDED`
- Managed key store / KMS selection for SEC-3.1 / SEC-5.x. — `TO BE DECIDED`
- Hosting cloud, region, and data residency for cross-border transfer (PRIV-1.12, §14). — `TO BE DECIDED`
- Hybrid post-quantum key exchange support (SEC-5.4) — depends on chosen platform/providers. — `TO BE DECIDED`
- Later-phase integrations (Microsoft Graph, CardDAV, calendar, SMS/WhatsApp/Signal delivery)
  (§2.2, INT-3.x, INT-5.x). — `TO BE DECIDED`
- Direct third-party (contact) erasure intake and identity verification (PRIV-1.4, §14). — `TO BE DECIDED`

---

## Dependency Rules

Directional rules that keep the architecture fail-closed, least-privilege, and tenant-isolated.
A violation of any rule is an architecture defect, not a style preference.

1. **Client trusts nothing; the API is the only authority.** The React client MUST NOT make
   authorization or data-scoping decisions; it presents what the API returns. All security
   invariants are enforced server-side (SEC-2.x).
2. **Every inbound edge validates against an explicit schema and rejects on failure.** User
   input, provider responses, and webhooks are validated before use; reject over sanitize.
   No component may consume another's output without validation at the boundary (SEC-4.1,
   FR-1.4).
3. **Authorization and consent fail closed.** Indeterminate authz, missing channel consent,
   or unknown timezone MUST deny / not deliver. Default-deny is the only default (SEC-2.3,
   FR-6.2, FR-3.3).
4. **All data access is user-scoped.** No code path may read or write across users. Every
   repository/query carries the owning user as a non-optional constraint (SEC-2.2).
5. **Secrets and tokens flow one way, into the encrypted-at-rest / KMS layer only.** No token
   or secret may reach the client, URLs, logs, or audit entries. Application code never holds
   raw key material (INT-1.6, SEC-3.1, SEC-8.2).
6. **Outreach links pass the scheme allowlist before reaching any sink.** No code path may
   place a URL into a DOM `href`/`src` or a reminder payload without passing the allowlist
   validator; failure resolves to `"#"` (FR-6.4, FE-1.3).
7. **Integration adapters are least-privilege and independently revocable.** Each adapter
   requests only its function's scopes and is isolated so that revoking or removing one cannot
   affect another (INT-1.7, FR-1.5).
8. **Reminder generation is idempotent and capped.** The Scheduler→Delivery path must be safe
   to re-run and must enforce per-user/window caps; no component downstream may assume
   exactly-once without the idempotency key (FR-5.2, SEC-6.2).
9. **Privacy operations cascade completely.** Deletion/erasure MUST reach every store holding
   the subject's data (primary tables, derived data, tokens, and scheduled retention of
   backups); no component may retain orphaned personal data (FR-1.3, PRIV-1.6).
10. **Dependencies are minimized and vetted.** New third-party libraries require CVE,
    maintenance, and transitive-footprint review; builds fail on new high-severity findings;
    SBOM and pinned, integrity-verified versions are mandatory (SEC-9.x).
11. **Design tokens are the only styling source.** UI components consume DESIGN.md tokens;
    hard-coded colors/sizes are disallowed so rebrand/theming stays centralized (DESIGN.md §7.1).
