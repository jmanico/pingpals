# Record of Processing Activities (RoPA) — Pingpals

**Article 30 GDPR.** Status: Draft for advisor review (PRIV-1.10). Maintained by the controller.

> This RoPA is an accountability artifact required before production launch. The lawful-basis and
> DPIA positions below MUST be reviewed and signed off by a qualified data-protection advisor
> (REQUIREMENTS.md §14, PRIV-1.1/1.11) — a standing human gate, not yet cleared.

## 1. Controller

- **Controller:** the operator of the Pingpals service (single-tenant per account owner).
- **Contact for data protection:** `[PLACEHOLDER: DPO / privacy contact]`.

## 2. Processing activities

| # | Activity | Purpose | Lawful basis | Data subjects | Data categories |
|---|---|---|---|---|---|
| P1 | Account & authentication | Provide the service to the user | Art. 6(1)(b) contract | User (account owner) | OIDC `sub`, session material, MFA credentials |
| P2 | Contact cadence reminders | Remind the user to stay in touch | Art. 6(1)(f) legitimate interests (LIA) | Contacts (third parties) | Name, phone, email, category, notes, last-contact history |
| P3 | Contact import (opt-in) | Populate contacts at least privilege | Art. 6(1)(f) + user consent for the integration | Contacts | Name, phone, email, stable provider id |
| P4 | Calendar free/busy (opt-in) | Meeting-aware cadence | Art. 6(1)(f) + consent | User | Free/busy windows only |
| P5 | Mailbox metadata detection (opt-in, default off) | Auto last-contact detection | Art. 6(1)(f) + explicit recorded consent | User + correspondents | Gmail message **metadata/headers only** |
| P6 | Reminder delivery | Notify the user on consented channels | Art. 6(1)(b)/(f) + per-channel consent | User | Delivery endpoint, minimal reminder reference |
| P7 | Audit & accountability | Security, GDPR Art. 5(2) accountability | Art. 6(1)(c)/(f) | User | Tamper-evident event log (no message content) |

## 3. Recipients / processors

Transactional email provider, SMS provider, hosting, managed KMS — each `TO BE DECIDED` and each to
be covered by a **Data Processing Agreement** (PRIV-1.12) before production. Signal is self-hosted
on infrastructure the user controls.

## 4. International transfers

Hosting region and data residency are deferred (cloud-agnostic). A valid transfer mechanism (e.g.
Standard Contractual Clauses) MUST be in place where applicable before launch (PRIV-1.12, §14).

## 5. Retention

See [retention schedule](#retention) below and `privacy/retention.py`. Operational PII is deleted
on an automated schedule (PRIV-1.9). Security/DSR/accountability events are retained for a distinct
accountability period that is not shorter than operational retention (SEC-8.4). Backups/snapshots
are encrypted, key-separated, and within the same purge schedule (SEC-5.6).

## 6. Security measures

Zero-Trust, fail-closed, per-user isolation, encryption in transit (TLS 1.3) and at rest
(AES-256-GCM under managed keys), partitioned decrypt authority, tamper-evident audit log,
least-privilege OAuth scopes. See SECURITY.md.

<a name="retention"></a>
## 7. Retention schedule (summary)

| Data class | Retention | Mechanism |
|---|---|---|
| Operational PII (reminders, contact events, outreach history) | `[PLACEHOLDER: e.g. 24 months]` | `RetentionJob` (PRIV-1.9) |
| Consent records | Accountability period (immutable) | append-only; survive operational purge |
| Audit / DSR / security events | Accountability period (≥ operational) | sealed-segment purge, chain re-anchored (SEC-8.4) |
| Export artifacts | Short bounded window | single-use token + retention purge (PRIV-1.17) |
| Backups / snapshots | Documented purge schedule | encrypted, key-separated (SEC-5.6) |
