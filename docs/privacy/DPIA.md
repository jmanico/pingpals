# Data Protection Impact Assessment (DPIA) — Pingpals

**Article 35 GDPR.** Status: Draft for advisor review (PRIV-1.11). MUST be completed and signed off
by a qualified data-protection advisor **before production launch** (REQUIREMENTS.md §14).

## 1. Why a DPIA is required

Pingpals systematically processes personal data of **third-party data subjects (the contacts) who
are not users**, including optional mailbox-metadata detection. This systematic processing of
non-user data triggers a DPIA (PRIV-1.11).

## 2. Description of processing

See RoPA P1–P7. The product nudges a single user to maintain contact at a self-set cadence and
hands them a validated one-tap deep link; **the system never sends messages into third-party
platforms on the user's behalf** — a deliberate boundary that minimizes data exposure, third-party
API surface, and lawful-basis complexity (REQUIREMENTS.md §1).

## 3. Necessity & proportionality

- **Data minimization** (PRIV-1.7): only name, phone, email, stable provider id, category, and
  user-entered notes are stored for a contact; imports are field-limited (INT-4.2).
- **Purpose limitation** (PRIV-1.8): contact data is used only for reminders; notes are display-only.
- **Privacy by default** (PRIV-1.13): integrations off, mailbox detection off, minimum scopes.

## 4. Risks & mitigations

| Risk | Mitigation | Residual |
|---|---|---|
| Cross-user data exposure (BOLA) | Non-optional owner scoping at the repository; per-request PDP; isolation tests | Low |
| Token/credential compromise | Encryption at rest, managed KMS, partitioned decrypt, no raw keys in app | Low |
| Mailbox-metadata over-collection | `gmail.metadata` scope only, opt-in, default off, puringe on disable (FR-4.4) | Medium — recorded here |
| **Article 9 special-category data in free-text notes** | Point-of-entry notice; notes are display-only and never derived/indexed (PRIV-1.18) | **Residual — see §5** |
| Reminder payload leakage via processors | Minimal/opaque payloads; RFC 8291 encryption or opaque id on untrusted surfaces (FR-5.6) | Low |
| Audit tampering | Hash chain + external anchor + active verification (SEC-8.5) | Low |

## 5. Article 9 residual-risk decision (PRIV-1.18)

Free-text notes can capture special-category data (health, religion, relationship details) for which
**no Article 9 lawful-processing condition is established** (PRIV-1.1 covers only Art. 6(1)(f)). The
chosen mitigation is: (a) a point-of-entry notice advising against entering such data; (b) treating
notes as **display-only** — never a processing input; (c) failing closed to display-only absent an
established Article 9 condition. This residual risk is **accepted pending advisor sign-off**.

## 6. Lawful basis

Legitimate interests (Art. 6(1)(f)) for contact personal data, supported by the [LIA](./LIA.md);
contract (Art. 6(1)(b)) for account data (PRIV-1.1). The household-activity exemption (Art. 2(2)(c))
may shield an end user's purely personal use but does **not** exempt the controller operating the
service.

## 7. Outcome

`[PLACEHOLDER: advisor conclusion + sign-off date]` — **not yet cleared** (standing human gate, §14).
