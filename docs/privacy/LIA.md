# Legitimate Interests Assessment (LIA) — Pingpals

**Article 6(1)(f) GDPR.** Status: Draft for advisor review (PRIV-1.1). MUST be signed off by a
qualified data-protection advisor before production launch (REQUIREMENTS.md §14).

Covers the processing of **contact (third-party) personal data** for relationship-cadence reminders
(RoPA P2/P3/P5). Account data is processed under contract, Art. 6(1)(b), and is out of scope here.

## 1. Purpose test — is there a legitimate interest?

Yes. The user has a genuine interest in maintaining their personal and professional relationships
and not letting contact lapse. Helping a single user remember to reach out is a clear, lawful, and
real interest. Pingpals does not message contacts, market to them, profile them, or enrich them from
data brokers (REQUIREMENTS.md §2.3).

## 2. Necessity test — is the processing necessary?

Yes, and minimized. To remind the user, the system needs the contact's name and a way for the user
to reach them (phone/email) plus a category/cadence. Imports are limited to name/phone/email/stable
provider id (INT-4.2). Optional mailbox detection uses **metadata/headers only** (FR-4.4). No less
intrusive means achieves the reminder purpose.

## 3. Balancing test — do the interests override the data subject's rights?

| Factor | Assessment |
|---|---|
| Reasonable expectations | A contact would reasonably expect the user to keep their details to stay in touch. |
| Nature of data | Ordinary contact data; **special-category data is discouraged** and display-only (PRIV-1.18). |
| Impact on the contact | Minimal — the contact is not messaged by the system; data stays under the user's control. |
| Safeguards | Per-user isolation, encryption, minimization, retention limits, DSR support, controller-mediated erasure (PRIV-1.4). |

The balancing favours the legitimate interest, given the minimization and safeguards and the
non-actor boundary. Special-category data in notes is the key residual risk (see DPIA §5).

## 4. Data-subject rights

Contacts (non-users) hold GDPR rights exercisable via a documented intake channel; the MVP model is
**controller-mediated erasure** (the user erases the contact — FR-1.3 cascade), plus a manual DSR
process (PRIV-1.4). Direct identity-verified third-party intake is **DECISION 075**.

## 5. Conclusion

Legitimate interests is an appropriate basis for contact personal data, subject to the documented
safeguards and **advisor sign-off** (not yet cleared — REQUIREMENTS.md §14).
