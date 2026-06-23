# [EPIC] Pingpals MVP build

## Objective

Deliver the Pingpals MVP defined in `REQUIREMENTS.md` §2.1: a **single-user**
relationship-cadence reminder **web + API application** that nudges the account owner to stay
in touch with people they track, at a per-relationship cadence they set, and hands them a
**validated one-tap outreach deep link** to open the conversation in their *own* messaging app
— the system never sends messages into third-party platforms on the user's behalf. The build
realizes the React 19 (client-only) SPA + Flask REST architecture of `ARCHITECTURE.md` under
the Zero-Trust, fail-closed, GDPR-by-default secure-coding baseline of `SECURITY.md`, with the
brand/UX of `DESIGN.md`. Every sub-issue below cites the governing requirement tag(s); nothing
is built beyond the four specs, and all undecided infrastructure is tracked as explicit
**decision** issues rather than guessed.

## How to use this epic

- Each sub-issue is authored against `REQUIREMENT_TEMPLATE.md`, is single-responsibility,
  independently testable, and scoped to ~0.5–2 days (< 1500 LOC). Acceptance criteria are taken
  verbatim from each spec's **"Verification:"** clauses where present.
- **Model recommendation** per issue: **Opus 4.8 (O)** for security/crypto/auth/audit/
  GDPR-correctness/threat-sensitive logic where a subtle error is a vulnerability;
  **ChatGPT 5.5 (G)** for well-bounded CRUD, schema/DTO, UI scaffolding, token/config/CI, and
  docs. The recommendation is also recorded inside each issue's *Implementation Notes → AI
  Development Guidance*. It is advisory; both models are capable.
- **Dependency flow:** Foundations (A) + backend core (B) → Auth (C) → Contacts (D) → Engine
  (E) and Delivery (F) → with Privacy/DSR (G) in parallel; Frontend (H) trails the API it
  consumes; Testing (I) is continuous. **Decision** issues (J) gate their dependents and must be
  resolved (with human sign-off per `CLAUDE.md`) before the blocked code is written.

## Sub-issues

<!-- TASKLIST -->

## Open Questions (resolved + still-open)

Resolutions are recorded in the specs (REQUIREMENTS.md §14, ARCHITECTURE.md). The list below
tracks what is resolved vs. what remains open. Code issues that depend on a still-open item keep
the choice behind an interface and default to the most restrictive option until its decision
issue is resolved.

**Resolved (decisions made):**

- **Database engine → PostgreSQL** (behind a repository interface; also backs server-side
  sessions). Decision 069 resolved.
- **In-app/push → standard Web Push** (own VAPID keys + RFC 8291 payload encryption),
  provider-agnostic. Decision 071 resolved.
- **Post-quantum → migration-ready classical baseline** (TLS 1.3 + crypto-agility + rotation);
  no PQ algorithm committed. Decision 074 resolved.
- **CI → GitHub Actions + OSS scanners** (provider-agnostic definition); **SBOM → CycloneDX**;
  **container base → official slim, digest-pinned, non-root**.
- **Scope promoted into MVP:** all contact providers (Google People + Microsoft Graph + CardDAV
  + Apple/iCloud CardDAV); Google Calendar read-only (free/busy); Gmail metadata-only
  last-contact detection (opt-in, default off); and SMS / WhatsApp / Signal delivery (Signal =
  self-hosted signal-cli, best-effort, not officially supported, off by default). The `[LATER]`
  trackers 076–079 are promoted; their MVP work is folded into the contacts/calendar/delivery
  issues.
- **Direct third-party erasure → controller-mediated** (the user deletes the contact) + a
  documented manual DSR process for MVP. Decision 075 resolved for MVP.
- **Brand:** fonts → **self-hosted SIL OFL set** (Cinzel/Playfair/Inter/Poppins, Trajan dropped);
  mascot → **small ~3-expression set**; dark mode → **token-ready, deferred**.

**Still open / deferred (kept visible):**

- **Infrastructure (behind interfaces, default-deny):** durable queue/broker (**[DECISION]
  Queue/broker** 070), managed KMS vendor (**[DECISION] KMS vendor** 072), transactional email
  provider (038), SMS provider (deferred behind the signature-verifying interface), and the
  audit-chain external anchor store. Plus **hosting cloud/region/data residency** (**[DECISION]
  Hosting/region** 073) and **orchestrator** — both deferred (cloud-agnostic); the region
  deferral blocks finalizing processor DPAs (`PRIV-1.12`).
- **GDPR lawful basis & DPIA — position confirmed, sign-off pending.** Basis confirmed
  (legitimate interests for contact data; contract for account data); the LIA and Article 35
  DPIA still require qualified data-protection-advisor sign-off **before production launch**
  (`PRIV-1.1`, `PRIV-1.11`, §14). Tracked in **[PRIVACY] RoPA + DPIA + LIA**.
- **Future direct third-party erasure beyond controller-mediated** — identity-verified,
  possibly cross-user intake remains open and needs DPO/legal sign-off (**[DECISION] Direct
  third-party erasure intake** 075).
- **Exact brand hex values** — color-pick against vector art before production (non-blocking).
- **Operational alerting destination** — deferred behind an alerting abstraction.
