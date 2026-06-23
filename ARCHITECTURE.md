# Pingpals: ARCHITECTURE.md

**Project:** Pingpals (personal relationship cadence and reminder system)
**Document:** ARCHITECTURE.md
**Version:** 0.1.0
**Status:** Provisional (bootstrap — no implementation exists yet)
**Companion documents:** [REQUIREMENTS.md](./REQUIREMENTS.md) (what the system must do), [DESIGN.md](./DESIGN.md) (look and feel)

> `TO BE DECIDED` marks undecided choices. REQUIREMENTS.md is the source of truth and wins on any conflict.

---

## Required Architecture Inputs

> Product context: REQUIREMENTS.md §1,§2,§4,§5,§10. Brand: DESIGN.md §1–§7. Security: SECURITY.md (of record: REQUIREMENTS.md §7–§8). Below: only the tech choices this document owns.

```
Runtime environment: web application
Server framework: Python Flask
Client framework: ReactJS (React 19, client-only, function components + hooks, no SSR — FE §9)
API style and integration model: REST
Authentication and session model: OIDC (Google) SSO + WebAuthn/passkey + MFA, no password-only.
  Control rules (cookies, lifetimes, PKCE, revocation) are authored in SECURITY.md §2;
  requirements of record are REQUIREMENTS.md SEC-1.x, INT-1.x.
Data model expectations: Per-user isolated data set. Core entities: User, Contact, Category,
  Cadence (interval days + optional preferred day/send window), Reminder, ConsentRecord,
  ContactEvent (last-contact log), OutreachAction, ProviderToken (encrypted), AuditLogEntry.
  Data classes and minimization rules are owned by REQUIREMENTS.md §3, §6.4, PRIV-1.7.
Deployment model: Docker container (cloud-portable; runs on many clouds). Specific
  orchestrator/cloud TO BE DECIDED.
```

---

## Initial Architecture (Provisional)

A client-only React 19 SPA over REST/TLS 1.3 to a Flask API, the single trust boundary
(per-request authz, fail closed). An internal Scheduler evaluates cadence and enqueues
reminders to a Delivery worker. Third-party access is least-privilege OAuth. Outreach never
leaves the user's device: the API returns only a validated deep link for the client to open.

**Components (logical, not a file layout):**

Control rules live in SECURITY.md; tags in parentheses are the REQUIREMENTS.md lookup.

- **Web client (React 19 SPA).** Client-only, no SSR. Validates input and API responses,
  sanitizes every `href`/`src`, enforces strict CSP, and consumes DESIGN.md tokens for all
  styling (DESIGN.md §7.1). Enforces FE-1.1–1.8, FR-6.4 — see SECURITY.md §4.
- **API service (Flask, REST).** Stateless behind cookie sessions; the single trust boundary.
  Validates and rejects external input, enforces per-request authz and per-user scoping on
  every endpoint, contextually encodes output, and rate-limits sensitive endpoints. Enforces
  FR-1.4, SEC-2.x, SEC-4.x, SEC-6.1 — see SECURITY.md §1, §3, §4, §7.
- **AuthN/Session subsystem.** OIDC (Google) SSO + WebAuthn/passkeys with MFA, no
  password-only path; OAuth Authorization Code + PKCE for all providers. Enforces SEC-1.x,
  INT-1.x — see SECURITY.md §2.
- **Scheduler service.** Per-user cadence evaluation: emits a reminder when
  `now − last_contacted ≥ effective_cadence` AND within send window AND channel consent
  present AND no active snooze (FR-5.1). Idempotent generation, fails closed on unknown
  timezone, caps reminders per user per window, horizontally scalable by user shard
  (FR-3.3, FR-5.2, SEC-6.2, NFR-1.1 — see SECURITY.md §7).
- **Delivery worker.** Sends to the user via email and in-app/push (MVP). Per-channel
  affirmative consent required, retries + dead-letter, minimal payload (display name,
  channel, outreach action only) (FR-5.4, FR-6.2, NFR-1.2 — see SECURITY.md §9).
- **Outreach-link service.** Builds deep links (`mailto`, `tel`, `sms`, `https` wa.me,
  Signal) behind an allowlist validator; the system never transmits into those platforms
  (FR-6.3, FR-6.4, SEC-4.3 — see SECURITY.md §4).
- **Integration adapters.** Google People (contacts read, least scope) in MVP; transactional
  email provider. Each independently revocable; tokens purged on disconnect/erasure
  (FR-1.5, INT-1.7, SEC-3.3 — see SECURITY.md §5). Later: Microsoft Graph, CardDAV, calendar,
  SMS/WhatsApp/Signal.
- **Privacy/DSR subsystem.** Consent records, machine-readable export, hard-delete erasure
  cascade, automated retention job, privacy-by-default (PRIV-1.2, 1.5, 1.6, 1.9, 1.13 — see
  SECURITY.md §9).
- **Persistence + secret/key management.** Encrypted-at-rest Restricted data with keys in a
  managed key store (app code holds no raw key material); crypto-agile and rotatable;
  tamper-evident append-only/hash-chained audit log (SEC-3.1, SEC-5.2, SEC-5.3, SEC-8.x —
  see SECURITY.md §5, §6).

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

Directional dependency constraints (who may depend on whom). Control rules are authored in SECURITY.md; tags shown are the REQUIREMENTS.md lookup.

1. **Client depends on the API for all authority.** The React client makes no authorization or
   data-scoping decisions; it presents what the API returns (SEC-2.x — see SECURITY.md §3).
2. **No component consumes another's output without boundary validation.** Every inbound edge
   validates against an explicit schema and rejects on failure (FR-1.4, SEC-4.1 — see
   SECURITY.md §4).
3. **Indeterminate decisions resolve to deny.** Authz, channel consent, and timezone
   resolution fail closed (SEC-2.3, FR-6.2, FR-3.3 — see SECURITY.md §3, §9).
4. **Every repository/query carries the owning user as a non-optional constraint.** No code
   path reads or writes across users (SEC-2.2 — see SECURITY.md §3).
5. **Secrets and tokens flow one way, into the encrypted-at-rest / KMS layer only** — never to
   the client, URLs, logs, or audit entries (INT-1.6, SEC-3.1, SEC-8.2 — see SECURITY.md §5).
6. **No URL reaches a sink without passing the scheme allowlist;** failure resolves to `"#"`
   (FR-6.4, FE-1.3 — see SECURITY.md §4).
7. **Integration adapters are isolated and independently revocable;** revoking or removing one
   cannot affect another (INT-1.7, FR-1.5 — see SECURITY.md §5).
8. **The Scheduler→Delivery path is idempotent and capped;** no downstream component assumes
   exactly-once without the idempotency key (FR-5.2, SEC-6.2 — see SECURITY.md §7).
9. **Erasure reaches every store holding the subject's data;** no component retains orphaned
   personal data (FR-1.3, PRIV-1.6 — see SECURITY.md §9).
10. **New third-party dependencies are minimized and vetted before introduction** (SEC-9.x —
    see SECURITY.md §8).
11. **UI components depend on DESIGN.md tokens for styling, never hard-coded values** (DESIGN.md §7.1).
