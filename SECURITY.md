# Pingpals: SECURITY.md

**Project:** Pingpals (personal relationship cadence and reminder system)
**Document:** SECURITY.md — Secure-Coding Baseline
**Version:** 0.1.0
**Status:** Provisional (bootstrap — no implementation exists yet)
**Conformance:** The keywords MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are interpreted per RFC 2119 and RFC 8174 when used in all capitals.
**Companion documents:** [REQUIREMENTS.md](./REQUIREMENTS.md) (what the system must do), [ARCHITECTURE.md](./ARCHITECTURE.md) (how it is built), [DESIGN.md](./DESIGN.md) (look and feel).
**Primary references:** OWASP Top 10 Proactive Controls, OWASP Cheat Sheet Series, OWASP API Security Top 10, OWASP REST Security Cheat Sheet, OWASP AISVS, and the standards already anchored in REQUIREMENTS.md §13 (RFC 9700, RFC 9068, NIST SP 800-207, NIST SP 800-53 Rev. 5, GDPR, FIPS 203, TLS 1.3).

> This is the secure-coding contract for any code added to this repository. It compresses the
> project's own requirements plus authoritative public references into short, high-signal rules an
> AI coding agent (and humans) can apply while writing Flask/React code. It is the security peer to
> the other three documents. **REQUIREMENTS.md remains the source of truth; where this document and
> REQUIREMENTS.md disagree, REQUIREMENTS.md wins.** Rules paraphrase their sources — consult the
> cited requirement tag or reference for full detail before relying on an edge case.

---

## How To Use This File

- Treat every rule as a default-deny invariant: if you cannot satisfy it, stop and fail closed
  rather than ship the weaker path.
- Each rule is tagged with the requirement it compresses (e.g. `SEC-2.2`, `FR-6.4`, `PRIV-1.6`) or
  the external standard it derives from. Tags are the lookup key back into REQUIREMENTS.md.
- Where the stack is not yet decided, rules carry `TO BE DECIDED` forward rather than guessing.
  Do not invent infrastructure choices to satisfy a rule; raise the open input instead.

---

## Required Security Inputs

What is **fixed** today (from ARCHITECTURE.md and REQUIREMENTS.md), and therefore binding on all code:

- **Backend:** Python **Flask**, **REST** API, stateless behind cookie sessions, TLS 1.3 only.
- **Frontend:** **React 19**, client-only (no SSR, no Node APIs), function components + hooks, Zod
  validation, strict CSP.
- **Auth:** OIDC (Google) SSO + **WebAuthn/passkey** + **MFA**; no password-only path. OAuth
  Authorization Code + PKCE (S256) for all providers.
- **Posture:** **Zero Trust** (NIST SP 800-207), fail-closed by default, per-request authorization,
  strict per-user tenant isolation, encryption at rest, crypto-agility.
- **Privacy:** **GDPR is in play** — the system processes personal data of third-party data subjects
  (the contacts) who are not users. Consent, DSR, erasure cascade, retention, and a DPIA before
  launch are mandatory.
- **Packaging:** **Docker** container image, cloud-portable.

What is still **needed** before these rules can fully harden (mirrors ARCHITECTURE.md `TO BE DECIDED`).
Until each is decided, code MUST keep the choice behind an interface and default to the most
restrictive option:

- Database engine and schema realization. — `TO BE DECIDED`
- Durable queue / broker for reminder enqueue, retry, dead-letter. — `TO BE DECIDED`
- In-app/push delivery mechanism and provider. — `TO BE DECIDED`
- Managed key store / KMS vendor (interface-abstracted, no proprietary lock-in in MVP). — `TO BE DECIDED`
- Hosting cloud, region, and data residency (bounds cross-border transfer obligations). — `TO BE DECIDED`
- Orchestration (plain Docker vs. Kubernetes). — `TO BE DECIDED`
- Hybrid post-quantum key exchange support (depends on chosen platform/providers). — `TO BE DECIDED`
- Direct third-party (contact) erasure intake and identity verification. — `TO BE DECIDED`

---

## Provisional Security Rules

Grouped by priority area. Rules are imperative and durable; they are safe to follow before any
infrastructure is chosen.

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

### 3. Authorization & tenant isolation

- Every request MUST be **authorized per-request** against the authenticated user; no trust from
  prior auth or network position (`SEC-2.1`, ARCH Dependency Rule 1).
- **All data access MUST be user-scoped.** Every repository/query MUST carry the owning user as a
  non-optional constraint; no code path may read or write across users (`SEC-2.2`, ARCH Rule 4).
- Authorization decisions MUST **fail closed**: an indeterminate or errored policy decision MUST deny
  (`SEC-2.3`, ARCH Rule 3).
- The React client MUST NOT make authorization or data-scoping decisions; it presents what the API
  returns. All security invariants are enforced server-side (ARCH Rule 1).

### 4. Input validation & output handling

- Every inbound edge — user input, **provider responses**, and **webhook payloads** — MUST be
  validated against an explicit schema and **rejected on failure**. Reject over sanitize; provider
  responses are untrusted until validated (`SEC-4.1`, `FR-1.4`, ARCH Rule 2).
- All output rendered in any web context MUST be **contextually encoded**. Never construct HTML from
  untrusted strings (`SEC-4.2`).
- On the client, all form input and all API response data MUST be validated with **Zod** before use
  (`FE-1.2`).
- **Outreach URLs MUST pass an allowlist scheme validator before reaching any sink.** Allowed:
  `mailto`, `tel`, `sms`, `https` (restricted to the click-to-chat host, e.g. `wa.me`), and the
  Signal scheme. Anything else (e.g. `javascript:`, `data:`) MUST resolve to the safe fallback `"#"`.
  No URL reaches a DOM `href`/`src` or a reminder payload without passing this validator
  (`FR-6.4`, `SEC-4.3`, `FE-1.3`, ARCH Rule 6).

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

### 6. Logging & error handling

- Produce **tamper-evident** audit logs (append-only or hash-chained) for authentication events,
  authorization denials, integration token use, DSR actions, and deletions (`SEC-8.1`).
- Audit and operational logs MUST NOT contain secrets, tokens, message content, or unnecessary
  personal data; PII in logs is minimized and retention-bound (`SEC-8.2`, `NFR-1.3`).
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
- CI MUST run **SAST, SCA, secret-scanning, and dependency checks**, and MUST **block merge** on
  failure or on newly introduced high-severity findings (`SEC-9.2`, `TEST-1.6`).
- Generate an **SBOM**; pin dependency versions with **integrity verification** (`SEC-9.3`).
- **Docker image hardening:** run as a **non-root** user, use a minimal/pinned base image, install no
  build toolchain into the runtime layer, bake in no secrets, and keep the image free of debug
  servers (Flask debug mode MUST be off in any non-dev image).
- Cloud, orchestrator, region, and KMS deployment specifics are `TO BE DECIDED`; until chosen, keep
  them behind interfaces and default to least privilege and least exposure.

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

## Prompt Placeholders To Resolve

The stack is identified in ARCHITECTURE.md, so five of six placeholders resolve to concrete rule
sets; deployment is partial because cloud/orchestrator/region/KMS remain `TO BE DECIDED`.

### `{{CODE_QUALITY_PROMPT}}` — *Resolved (default)*
Keep **low cyclomatic and low cognitive complexity** and clear **separation of concerns**. Small,
single-responsibility functions; isolate I/O, validation, and business logic; no security-relevant
branch buried in a deeply nested path. Maintain ≥80% statement coverage as a CI gate (`TEST-1.1`).

### `{{API_SECURITY_PROMPT}}` — *Resolved (REST confirmed)*
Apply the **OWASP API Security Top 10** and **REST Security Cheat Sheet**, compressed:
- Enforce object- and function-level authorization on every endpoint (no BOLA/BFLA); reject
  cross-user object access with not-found/forbidden (`SEC-2.2`).
- Validate and bound all input; reject unknown fields; never mass-assign.
- Use correct HTTP methods/status codes; disable verbose errors; no internal IDs leaked.
- Rate-limit and resource-cap sensitive endpoints (`SEC-6.1`).
- JSON only; set `Content-Type` explicitly; never echo unvalidated input into responses.

### `{{BACKEND_FRAMEWORK_PROMPT}}` — *Resolved (Flask confirmed)*
Flask web-security essentials, compressed:
- `debug=False` in any non-dev build; never expose the Werkzeug debugger/PIN.
- Set a strong, secret `SECRET_KEY` from the secret store (never hard-coded); rotate per `SEC-3.x`.
- Cookies: `Secure`, `HttpOnly`, `SameSite` (`SESSION_COOKIE_*`) — see Rule 2.
- Rely on Jinja autoescaping; never disable it or render untrusted strings as markup (`SEC-4.2`).
- Validate request bodies/params against explicit schemas; reject on failure (`FR-1.4`, `SEC-4.1`).
- Apply security headers and CSP at the response layer (Rule 1).

### `{{FRONTEND_FRAMEWORK_PROMPT}}` — *Resolved (React 19 confirmed)*
React 19 secure-by-default, compressed (REQUIREMENTS.md §9):
- `dangerouslySetInnerHTML` MUST NOT be used (`FE-1.1`).
- Every `href`/`src` passes `validateAndSanitizeUrl`, returning `"#"` on failure (`FE-1.3`).
- Do not spread props onto DOM nodes (`FE-1.5`); do not use array-index keys for dynamic lists —
  use `crypto.randomUUID` when no stable domain id exists (`FE-1.6`).
- Guard `useEffect` data fetches against races with `AbortController`/ignore flag and clean up on
  unmount (`FE-1.7`).
- Validate all props/API data with Zod (`FE-1.2`); keep the app CSP-friendly (`FE-1.4`).

### `{{AUTH_PROMPT}}` — *Resolved (auth model confirmed)*
**OWASP Authentication & Session Management** cheat sheets, plus **RFC 9700** (OAuth BCP) and
**WebAuthn**, compressed:
- WebAuthn/passkeys + MFA; no password-only path (`SEC-1.1`).
- Sessions in HttpOnly/Secure/SameSite cookies, idle+absolute lifetimes, server-revocable (`SEC-1.x`).
- OAuth Code+PKCE S256, exact redirect-URI match, `state`+`iss` validation, refresh rotation with
  family revocation (`INT-1.x`).
- Tokens never in URLs/logs/script-accessible storage (`INT-1.6`).

### `{{DEPLOYMENT_PROMPT}}` — *Partially resolved (Docker confirmed; cloud `TO BE DECIDED`)*
**Container hardening + OWASP CI/CD security**, compressed:
- Docker image: non-root user, minimal pinned base, no secrets baked in, no debug servers (Rule 8).
- CI gates: SAST, SCA, secret-scan, dependency check, SBOM, pinned + integrity-verified deps; block
  on new high-severity (`SEC-9.x`, `TEST-1.6`).
- Cloud provider, orchestration (Docker vs. k8s), region/data residency, and managed KMS vendor are
  `TO BE DECIDED` (ARCHITECTURE.md). Keep them interface-abstracted; default to least privilege and
  least exposure until decided.

---

## Selected Prompt Imports

Per the prompt, the rule sets selected above derive from these drivers:

| Driver | Source in repo | Selected import / rule-set | Status |
| --- | --- | --- | --- |
| Architecture decisions | ARCHITECTURE.md Initial Architecture + Dependency Rules | Zero Trust (NIST SP 800-207), fail-closed, per-request authz, tenant isolation | Resolved |
| Backend framework | ARCHITECTURE.md "Server framework: Python Flask" | Flask web-security guide (compressed) | Resolved |
| Frontend framework | ARCHITECTURE.md / REQUIREMENTS.md §9 "React 19" | React 19 secure-by-default rules (`FE-1.x`) | Resolved |
| Auth model | ARCHITECTURE.md / REQUIREMENTS.md §6.1, §8.1 | OWASP AuthN + Session Mgmt cheat sheets, RFC 9700, WebAuthn | Resolved |
| API style | ARCHITECTURE.md "API style: REST" | OWASP API Security Top 10 + REST Security Cheat Sheet | Resolved |
| Deployment model | ARCHITECTURE.md "Docker; cloud TBD" | Container hardening + OWASP CI/CD security; cloud / orchestrator / region / KMS `TO BE DECIDED` | Partial — `TO BE DECIDED` |
| Code quality | Cross-cutting (`TEST-1.1`) | Low cyclomatic/cognitive complexity, separation of concerns | Resolved (default) |

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

- The eight `TO BE DECIDED` inputs in **Required Security Inputs** above must be resolved before the
  corresponding rules can move from provisional to enforced.
- A **DPIA** (Art. 35) and a documented **Legitimate Interests Assessment** MUST be completed before
  production launch, given systematic processing that includes non-user data subjects
  (`PRIV-1.11`, REQUIREMENTS.md §14).
- Direct third-party (contact) erasure intake and identity verification remain an open decision
  (`PRIV-1.4`, REQUIREMENTS.md §14). Default for now: controller-mediated erasure (the user deletes
  the contact) plus a manual DSR process.
- Hosting region / data residency drives cross-border transfer obligations (`PRIV-1.12`) and is
  unresolved.
