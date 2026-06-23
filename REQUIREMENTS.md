# Pingpals: REQUIREMENTS.md

**Project:** Pingpals (personal relationship cadence and reminder system)
**Document:** REQUIREMENTS.md
**Version:** 0.1.0
**Status:** Draft
**Conformance:** The keywords MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are interpreted per RFC 2119 and RFC 8174 when used in all capitals.
**Primary references:** OWASP ASVS, OWASP AISVS, RFC 9700 (OAuth 2.0 Security BCP), RFC 6749, RFC 9068, NIST SP 800-207 (Zero Trust Architecture), NIST SP 800-53 Rev. 5, Regulation (EU) 2016/679 (GDPR), NIST FIPS 203 (ML-KEM), RFC 8446 (TLS 1.3), OWASP Cheat Sheet Series.

---

## 1. Purpose

Pingpals nudges a single user to maintain contact with people they choose to track, at a cadence they define per relationship.

The system does not act as the user on third-party platforms. It delivers the reminder to the user and hands them a one-tap action to open the conversation in their own messaging app. This boundary minimizes personal-data exposure, third-party API surface, platform terms-of-service risk, and GDPR lawful-basis complexity.

---

## 2. Scope

### 2.1 In scope (MVP)

- Manual contact creation and edit.
- Contact import at least-privilege contacts-read scope from Google People API, Microsoft Graph, CardDAV, and Apple Contacts (Apple realized as iCloud over CardDAV; no first-party server contacts API).
- Relationship categorization with shipped defaults and user-defined categories.
- Per-category and per-contact cadence configuration.
- Manual last-contact logging.
- Opt-in automatic last-contact detection from Gmail message **metadata/headers only** (never message bodies); default off; user may disable and purge all derived data at any time (FR-4.4). The added processing and its residual risk are recorded in the DPIA/LIA (PRIV-1.11, PRIV-1.1).
- Reminder engine (cadence evaluation and scheduling).
- Calendar **read-only (free/busy) for meeting-aware cadence** from Google Calendar (INT-3.1). No calendar event creation in MVP.
- Reminder delivery to the user via email, in-app or push, SMS, WhatsApp, and Signal. SMS, WhatsApp, and Signal are subject to the per-channel constraints of INT-5.x; Signal is a self-hosted, best-effort channel that MUST NOT be presented as officially supported (INT-5.3) and is off by default.
- One-tap outreach actions via validated deep links (mailto, tel, sms, WhatsApp click-to-chat, Signal).
- GDPR core: consent records, data export, erasure, retention enforcement.
- Security baseline per Section 8.

### 2.2 In scope (later phases)

- Calendar **event creation** (optional; MVP is calendar read-only) (INT-3.2).
- Additional mailbox-detection providers beyond Gmail (for example Microsoft Graph mail metadata).

### 2.3 Out of scope

- Sending messages to contacts on the user's behalf into any third-party messaging platform.
- Bulk or marketing messaging of any kind.
- Social graph inference or enrichment from external data brokers.
- LLM-generated outreach content. See Section 12 for the controls required if this is added later.

---

## 3. Definitions and data classification

- **Contact:** a natural person the user tracks. Personal data of a third-party data subject.
- **Category:** a relationship grouping with a default cadence.
- **Cadence:** target maximum interval between contacts, plus an optional send window.
- **Reminder:** a generated, due notification for one contact.
- **Channel:** how the user is notified (email, push, SMS, WhatsApp, Signal).
- **Outreach action:** a deep link that opens the user's own messaging app to the contact.
- **DSR:** data subject request (access, erasure, rectification, restriction, objection, portability).

**Data classification:**

- **Restricted:** contact personal data (name, phone, email, notes, category), OAuth tokens, consent records, audit logs.
- **Confidential:** user account credentials and session material.
- **Internal:** aggregate metrics containing no personal data.

---

## 4. Actors

- **User:** the account owner. Authenticated, sole controller of their own data set.
- **Contact (data subject):** not a system user. Holds GDPR rights exercisable through a documented channel.
- **Scheduler:** internal service that evaluates cadence and enqueues reminders.
- **Integration provider:** external OAuth-protected API (email, calendar, contacts, messaging).

---

## 5. Functional requirements (FR)

### 5.1 Contact management

- **FR-1.1** The system MUST allow a user to create a contact with at minimum a display name. All other fields MUST be optional.
- **FR-1.2** The system MUST allow edit and deletion of any contact owned by the user.
- **FR-1.3** Deletion of a contact MUST remove all associated personal data, reminders, and outreach history within the same transaction. Verification: a post-deletion query returns no rows for that contact across all tables.
- **FR-1.4** The system MUST validate all contact fields against an explicit schema and MUST reject invalid input rather than coercing it (reject over sanitize). Verification: an invalid phone or email is rejected with a field-level error and no partial write occurs.
- **FR-1.5** Contact import MUST request the minimum provider scope required to read contacts and MUST NOT request write or send scopes during import. MVP import providers are Google People, Microsoft Graph, CardDAV, and Apple Contacts (Apple realized as iCloud over CardDAV); each MUST use only its contacts-read scope and import only the fields permitted by INT-4.2. For CardDAV-based providers that authenticate by app-specific password rather than OAuth, the credential MUST be transported only over TLS and stored encrypted at rest per Section 8.3.

### 5.2 Relationship categorization

- **FR-2.1** The system MUST ship default categories: Best Friend, Casual Friend, Family, Professional. Each MUST have a configurable default cadence.
- **FR-2.2** The system MUST allow the user to create, rename, and delete custom categories, each with its own default cadence.
- **FR-2.3** Deleting a category MUST require reassignment of its contacts to another category and MUST fail closed if any contact would be left without a category.
- **FR-2.4** A contact MUST belong to exactly one category at a time.

### 5.3 Contact cadence

- **FR-3.1** Cadence MUST be expressed as a positive interval in days. The system MAY also store a preferred day of week and a send-time window.
- **FR-3.2** A contact MUST inherit its category default cadence unless a per-contact override is set. A per-contact override MUST take precedence.
- **FR-3.3** The user MUST be able to set quiet hours and a timezone. Reminders MUST NOT be delivered outside the allowed window. Timezone resolution MUST fail closed to no delivery when the timezone is unknown.

### 5.4 Last-contact tracking

- **FR-4.1** The system MUST allow the user to log a contact event (mark as contacted) with a timestamp defaulting to now.
- **FR-4.2** Logging a contact event MUST reset the cadence clock for that contact.
- **FR-4.3** Automatic last-contact detection from mailbox metadata is in MVP scope for Gmail and MUST be opt-in and default off per FR-4.4. Additional mailbox-detection providers (for example Microsoft Graph mail metadata) are later phase. The added processing and its residual privacy risk MUST be recorded in the DPIA and Legitimate Interests Assessment (PRIV-1.11, PRIV-1.1).
- **FR-4.4** If automatic detection is enabled, the system MUST request a read scope limited to message metadata (headers) only (for Gmail, the `gmail.metadata` scope), MUST NOT read message bodies, and MUST allow the user to disable it and purge all derived data at any time. Detection MUST default to off (privacy by default, PRIV-1.13) and MUST require affirmative, recorded consent for the optional processing (PRIV-1.2) before any mailbox is read.

### 5.5 Reminder engine

- **FR-5.1** The scheduler MUST generate a reminder for a contact when all of the following hold: now minus last contacted is greater than or equal to the effective cadence, the current time is within the allowed send window, the required channel consent is present, and no active snooze exists.
- **FR-5.2** Reminder generation MUST be idempotent. A single due event MUST NOT produce duplicate reminders. Verification: re-running the scheduler for the same window produces no additional reminders.
- **FR-5.3** The user MUST be able to snooze, dismiss, or mark a reminder as contacted. Mark as contacted MUST reset the cadence clock.
- **FR-5.4** The reminder payload MUST contain only the data needed to act (contact display name, chosen channel, outreach action). It MUST NOT embed tokens, secrets, or unnecessary personal data.
- **FR-5.5** Every enqueued reminder MUST carry its owning user as a non-optional attribute, and the privileged cross-user scope of the scheduler MUST NOT propagate to the delivery worker. At send time the delivery worker MUST re-verify, scoped to the reminder's owning user, that the chosen channel and the resolved delivery endpoint (for example email address or push subscription) belong to that same user and that channel consent (FR-6.2) is still present. Any mismatch, indeterminate ownership, or absent consent MUST fail closed: the reminder MUST be dropped, not delivered, and the denial MUST be recorded in the tamper-evident audit log (SEC-8.1). Verification: a reminder whose resolved delivery endpoint is owned by a different user, or whose ownership cannot be confirmed, is dropped rather than delivered, and an authorization-denial entry is written to the audit log.
- **FR-5.6** Where reminder delivery traverses a third-party processor (transactional email, web push), the system MUST fail closed on payload confidentiality. If the channel supports application-layer payload encryption to the delivery endpoint (for example Web Push message encryption per RFC 8291), the system MUST use it so the processor cannot read contact personal data in cleartext. If the channel cannot encrypt the payload end-to-end to the endpoint, or renders on an untrusted surface (push notification body, device lock screen), the delivered payload MUST NOT carry the contact display name or any other contact personal data; it MUST instead reference the reminder by an opaque, non-guessable id that reveals the contact only after an authenticated in-app fetch. This complements the minimal-payload rule FR-5.4. Verification: a captured push or email payload contains no contact personal data in cleartext outside an encrypted body, and a payload on an unencryptable or lock-screen-rendered channel contains only an opaque reminder id.

### 5.6 Multi-channel delivery

- **FR-6.1** The system MUST support delivery of the reminder to the user via email, in-app or push, SMS, WhatsApp, and Signal in MVP. Each non-email/push channel is subject to its per-channel constraints in INT-5.x: SMS requires inbound webhook signature verification (INT-5.1); WhatsApp requires the user's in-WhatsApp opt-in and respects the Cloud API session/template constraints (INT-5.2); Signal is a self-hosted, best-effort channel that MUST NOT be presented as officially supported (INT-5.3) and is off by default. Every channel is gated by per-channel consent (FR-6.2) and the per-channel concrete provider MAY be deferred behind the delivery interface (the SMS provider in particular is undecided; see §14).
- **FR-6.2** For each enabled channel the system MUST hold an affirmative, recorded consent for that channel. Absence of consent MUST fail closed (no delivery on that channel).
- **FR-6.3** Each reminder MUST offer one or more outreach actions implemented as deep links: mailto, tel, sms, WhatsApp click-to-chat (`https://wa.me`), and Signal. The system MUST NOT transmit any message into these platforms itself.
- **FR-6.4** Every outreach URL MUST pass an allowlist-based URL validator before rendering. Allowed schemes: `mailto`, `tel`, `sms`, `https` (restricted to the click-to-chat host), and the Signal scheme. For the `https` scheme the host MUST match a preregistered click-to-chat host allowlist (for example `wa.me`) by exact string comparison; suffix, substring, or wildcard host matching MUST NOT be used, so a lookalike such as `wa.me.evil.example` is rejected. Any contact-derived component (phone, handle) MUST be schema-validated and percent-encoded before insertion and MUST NOT be able to alter the scheme, host, or authority of the resulting URL; if it would, the URL MUST be rejected. Any other scheme or non-allowlisted host MUST be rejected and replaced with a safe fallback of `"#"`. Verification: a `javascript:` or `data:` scheme URL never reaches the DOM as an href, and an `https://wa.me.evil.example/...` lookalike-host URL is rejected to `"#"`.
- **FR-6.5** Every delivery endpoint (email address, web-push subscription, and any later-phase channel address) MUST be registered only within an authenticated session, verified by proof of control, and bound to exactly one owning user before it may receive any reminder; per-user scoping (SEC-2.2) applies to delivery endpoints as to all user data. Registering, replacing, or removing an endpoint MUST require the authenticated owning user and MUST NOT be possible by any unauthenticated or cross-user path. Before each delivery the worker MUST confirm the target endpoint is owned by the reminder's user and MUST fail closed (skip that channel) if ownership cannot be verified. Endpoints MUST be revoked and purged on logout, on withdrawal of that channel's consent (FR-6.2), and on account erasure (PRIV-1.6). Where push delivery routes a reminder through an intermediary outside the trust boundary, the payload MUST use an authenticated sender (for example VAPID) and message-level encryption and integrity protection (for web push, per RFC 8291/RFC 8030) so the intermediary cannot read or alter it — transport TLS (SEC-5.1) alone is insufficient because the intermediary terminates TLS; a mechanism that cannot apply message-level protection MUST fail closed (no push delivery). Outreach links carried in any payload remain subject to FR-6.4 on render. Verification: a subscription or address registered without ownership verification, or bound to a different user, receives no reminders; a delivery whose endpoint ownership cannot be verified is skipped, not sent; a reminder pushed through an intermediary cannot be read or modified in transit; and an endpoint revoked on logout, consent withdrawal, or erasure receives no further messages.

### 5.7 Notification preferences

- **FR-7.1** The user MUST be able to set a preferred channel order and per-category channel overrides.
- **FR-7.2** The user MUST be able to globally pause all reminders. While paused the scheduler MUST NOT enqueue or deliver reminders.

---

## 6. Integration requirements (INT)

### 6.1 OAuth baseline (all providers)

All third-party integrations MUST conform to RFC 9700 (OAuth 2.0 Security Best Current Practice) and the following:

- **INT-1.1** The Authorization Code flow with PKCE (S256) MUST be used for all clients. The implicit grant and the resource owner password credentials grant MUST NOT be used.
- **INT-1.2** Redirect URIs MUST be matched by exact string comparison against a preregistered allowlist.
- **INT-1.3** The authorization response MUST be validated, including the state parameter (CSRF defense) and the issuer (`iss`) parameter (mix-up attack defense).
- **INT-1.4** Access tokens MUST be short-lived. Refresh tokens MUST be rotated on use with replay detection that revokes the token family on reuse.
- **INT-1.5** Where the provider supports sender-constrained tokens (DPoP or mTLS), the system SHOULD use them.
- **INT-1.6** Tokens MUST NOT appear in URLs, logs, browser history, or any client-side storage accessible to scripts.
- **INT-1.7** Each integration MUST request the least-privilege scope set for its function and MUST be independently revocable by the user.
- **INT-1.8** Where an integration returns an OIDC ID token (the Google SSO login path), the ID token MUST be fully validated before any session is established. The token signature MUST be verified against the provider's published JWKS, and the `iss`, `aud` (which MUST equal the registered client id), `exp`, and `iat` claims MUST be checked. This is distinct from the INT-1.3 authorization-response `state`/`iss` validation. A single-use `nonce` MUST be generated per authorization request, bound to the initiating user agent, and matched against the returned ID token to defeat replay. Any validation failure MUST fail closed: no session is established and no session cookie is issued. References: RFC 9068, OIDC Core. Verification: an ID token with a wrong `aud`, an invalid or absent signature, an expired `exp`, or a missing or mismatched `nonce` is rejected and no session cookie is issued.
- **INT-1.9** A local user account MUST be bound to the IdP's immutable subject identifier (`sub`), scoped to the validated issuer (`iss`), and MUST NOT be keyed on, linked by, or merged on any mutable attribute such as email address or display name. Email MUST be treated as a non-authoritative display attribute only, and any email consumed MUST carry `email_verified` true. Identity resolution MUST fail closed: if `sub` is absent, or `email_verified` is false where an email is used, the login MUST be denied. Verification: changing, deleting, or recycling the IdP email for an address does not grant access to, lock out, or silently merge with another user's account, and a token whose `sub` does not match the bound account is rejected.
- **INT-1.10** Linking a provider identity or integration token to an account is an account-mutating action and MUST require a fresh authentication step (re-auth) by the session user before the link is committed. The resulting provider identity or token MUST be bound only to the user of the same session that initiated the authorization request, relying on the per-session `state`/PKCE binding of INT-1.1/INT-1.3; a callback whose session or re-auth binding does not match MUST fail closed and link no identity or token. Verification: a callback completed in, or replayed into, a session different from the one that initiated the flow, or one lacking the fresh re-auth, is rejected and links no identity or token.

### 6.2 Email integration

- **INT-2.1** MVP email delivery to the user MAY use a transactional email provider over an authenticated API. Provider credentials MUST be stored per Section 8.3.
- **INT-2.2** If a user mailbox is connected for last-contact detection (Gmail in MVP per FR-4.3), scope MUST be limited to message metadata read (for Gmail, `gmail.metadata`) and MUST NOT default to full mailbox read or request message-body access. Any later send-for-outreach-assist scope remains later phase and MUST be separately consented.
- **INT-2.3** The domain used to send reminder email to the user MUST be protected against sender spoofing so recipients can authenticate that the mail originates from Pingpals. SPF MUST be published, all reminder mail MUST be DKIM-signed, and the sending domain MUST publish a DMARC policy of `p=reject` with SPF and DKIM identifier alignment. A reminder-only domain has no legitimate third-party senders, so `reject` is the fail-closed default; `quarantine` MAY be used only as a temporary, time-boxed rollout step. Verification: legitimate reminder mail passes SPF and DKIM with DMARC alignment, and mail from an unaligned or unsigned source claiming the Pingpals sending domain fails DMARC and is rejected by a conformant receiver.

### 6.3 Calendar integration

- **INT-3.1** Calendar read for meeting-aware cadence is in MVP scope for Google Calendar and MUST be limited to free/busy or the event metadata necessary for meeting-aware cadence. Event content beyond what is required MUST NOT be stored.
- **INT-3.2** Calendar event creation is later phase (MVP is calendar read-only). If implemented, any event the system creates MUST be clearly attributed to Pingpals and MUST be deletable by the user.

### 6.4 Contacts integration

- **INT-4.1** Contact read MUST use the provider contacts read scope only. MVP providers are Google People, Microsoft Graph, CardDAV, and Apple Contacts (Apple realized as iCloud over CardDAV). OAuth providers (Google, Microsoft) MUST follow the INT-1.x baseline; CardDAV providers that authenticate by app-specific password MUST transport the credential only over TLS and store it encrypted per Section 8.3, and MUST NOT request any scope beyond contacts read.
- **INT-4.2** Imported fields MUST be limited to name, phone, email, and a stable provider id for deduplication. The system MUST NOT import unrelated profile data.

### 6.5 Messaging delivery to the user

- **INT-5.1** SMS delivery is in MVP scope and MUST verify inbound webhook signatures from the SMS provider before processing any callback (SEC-7.1). The concrete SMS provider is undecided and is kept behind the delivery interface (see §14); the signature-verification contract MUST be enforced regardless of provider.
- **INT-5.2** WhatsApp delivery to the user is in MVP scope, requires the user to have opted in within WhatsApp, and MUST respect the session (24-hour window) and template-message constraints of the WhatsApp Cloud API. Reminders sent outside an open session window MUST use a pre-approved template. The concrete WhatsApp Business/Cloud API account is kept behind the delivery interface.
- **INT-5.3** Signal has no sanctioned multi-tenant sending API. Signal delivery is in MVP scope only as a self-hosted single-user integration (e.g. signal-cli on infrastructure the user controls), MUST be labeled best effort, MUST default off, and MUST NOT be presented as an officially supported channel.

---

## 7. Privacy and GDPR requirements (PRIV)

Pingpals processes personal data of third-party data subjects (the contacts) who are not users, creating obligations beyond ordinary account-data handling.

- **PRIV-1.1** The controller MUST document a lawful basis for processing contact personal data. The expected basis is legitimate interests under Article 6(1)(f), supported by a documented Legitimate Interests Assessment. User account data is processed under contract, Article 6(1)(b).
- **PRIV-1.2** The system MUST record explicit, granular, withdrawable consent from the user for each notification channel and for any optional processing (for example, automatic last-contact detection). Both consent grant and consent withdrawal MUST be persisted as distinct events, each capturing a server-authoritative timestamp, the affected channel/scope, and the notice version, and each linked to the consent it establishes or revokes. These consent-change events MUST be carried in the tamper-evident audit trail required by SEC-8.1. The effective consent state for any channel at any past instant MUST be derivable from this event history; where it cannot be determined unambiguously, delivery on that channel MUST fail closed per FR-6.2. Verification: for any delivered reminder, the consent history shows an active grant for the chosen channel with no intervening withdrawal at the delivery timestamp.
- **PRIV-1.3** The system MUST implement data subject rights for the user: access and portability (Articles 15 and 20), rectification (Article 16), erasure (Article 17), restriction (Article 18), and objection (Article 21).
- **PRIV-1.4** The system MUST provide a documented intake channel for data subject requests originating from a contact (a non-user). For MVP the resolved model is **controller-mediated erasure**: the controlling user erases the contact (the FR-1.3 cascade), supported by a documented manual DSR intake channel for direct third-party requests. No automated cross-user purge mechanism is committed for MVP. Any future direct, identity-verified third-party erasure (including cross-user scope) remains an open decision in Section 14 and MUST have DPO/legal sign-off before implementation.
- **PRIV-1.5** Data export MUST be machine-readable (for example, JSON) and MUST include all personal data held for the requesting user. Verification: an exported file round-trips all contact, category, cadence, consent, and history records.
- **PRIV-1.6** Erasure MUST be a hard delete that cascades across contacts, reminders, outreach history, derived detection data, and provider tokens. Backups MUST be covered by a documented retention and purge schedule. Verification: an erasure test confirms no personal data for the subject remains in primary storage after completion.
- **PRIV-1.7** The system MUST enforce data minimization. Only the fields defined in Section 6.4 and the data classes in Section 3 may be stored. Verification: a schema audit shows no personal data fields outside the approved set.
- **PRIV-1.8** The system MUST enforce purpose limitation. Personal data collected for reminders MUST NOT be reused for any other purpose without a new lawful basis and notice.
- **PRIV-1.9** The system MUST enforce storage limitation through a configurable retention policy with an automated job that deletes data past retention. Verification: the retention job deletes records whose retention has elapsed and logs the action.
- **PRIV-1.10** The system MUST maintain a Record of Processing Activities per Article 30.
- **PRIV-1.11** A Data Protection Impact Assessment per Article 35 MUST be completed before production launch, given systematic processing of personal data that includes non-user data subjects.
- **PRIV-1.12** All processors (email, SMS, contacts, calendar, hosting) MUST be covered by a Data Processing Agreement. Cross-border transfers MUST rely on a valid transfer mechanism (for example, Standard Contractual Clauses) where applicable.
- **PRIV-1.13** Privacy by design and by default per Article 25 MUST be applied. Defaults MUST be the most privacy-protective available: integrations off, detection off, minimum scopes.
- **PRIV-1.14** A personal data breach MUST be assessed and, where required, notified to the supervisory authority within 72 hours per Article 33, with affected data subjects informed where Article 34 applies.
- **PRIV-1.15** Consent records MUST be append-only and immutable once written: granting or withdrawing consent MUST create a new record capturing timestamp, scope, and notice version (per PRIV-1.2), and an existing consent record MUST NOT be edited, deleted (outside erasure per PRIV-1.6), or have its timestamp or scope backdated. Per-channel delivery authorization (FR-6.2) MUST be evaluated only from the latest immutable consent record for that channel and MUST fail closed if record integrity cannot be established. Consent fields MUST NOT be settable through any general contact or preferences write (the no-mass-assignment rule, SECURITY.md §4, applies). Verification: an attempt to edit or backdate an existing consent record is rejected, delivery is authorized solely from the latest immutable record, and a missing or integrity-failed record yields no delivery on that channel.
- **PRIV-1.16** Every erasure (PRIV-1.6) and DSR fulfilment MUST produce a proof-of-action record in the tamper-evident audit log (SEC-8.1) that is explicitly excluded from the PRIV-1.6 cascade and therefore survives it. This record MUST contain no contact personal data: only a pseudonymous subject reference, the DSR type, the set of stores purged, the requesting principal, and the server-authoritative completion timestamp. The erasure MUST fail closed: it MUST NOT be reported complete until this record is durably committed to the tamper-evident log; if the record cannot be written or its tamper-evidence (hash chain) cannot be preserved, the erasure MUST abort rather than proceed without surviving proof. Verification: after an erasure, a post-deletion query returns no contact personal data for the subject (PRIV-1.6) yet a PII-free, tamper-evident proof-of-erasure record for that subject remains retrievable and its hash chain validates.
- **PRIV-1.17** The data export artifact (PRIV-1.5) is Restricted data and MUST be access-controlled to the requesting authenticated user only. Any download link MUST require the owner's authenticated session or a short-lived, single-use, unguessable token, MUST expire, and MUST NOT be a long-lived, unauthenticated, or enumerable URL. Access MUST fail closed: an unauthenticated, expired, already-used, or non-owner request MUST be denied. The artifact MUST be deleted on a bounded retention schedule (PRIV-1.9) and on the requesting user's erasure (PRIV-1.6); export generation and download are DSR actions and are therefore rate limited (SEC-6.1) and audited (SEC-8.1). Verification: an export download is rejected without the owner's authenticated session, after expiry, after first use, and for any other user, and no export artifact remains in storage after the bounded retention window or after the owner's erasure.
- **PRIV-1.18** Free-text fields holding contact personal data (notably the contact notes field, §3) are treated as Restricted and inherit all minimization, retention, export, and erasure controls of structured contact data. Because such fields can capture GDPR Article 9 special-category data (for example health, religion, or relationship details) for which no lawful-processing condition is established (PRIV-1.1 covers only Article 6(1)(f)), the system MUST advise the user at the point of entry that special-category data SHOULD NOT be entered, and the DPIA (PRIV-1.11) and Legitimate Interests Assessment (PRIV-1.1) MUST record this residual risk and the chosen mitigation. The system MUST NOT derive, index, or further process the contents of free-text notes for any purpose beyond display to the owning user (purpose limitation, PRIV-1.8); absent an established Article 9 condition the system fails closed to display-only. Verification: a privacy review confirms the point-of-entry notice is present, notes content is never used as a processing input beyond owner display, and the DPIA records the Article 9 residual-risk decision.

---

## 8. Security requirements (SEC)

Zero Trust per NIST SP 800-207, fail-closed by default; no request is trusted on the basis of network location.

### 8.1 Authentication

- **SEC-1.1** User authentication MUST be phishing resistant where possible. The system SHOULD use WebAuthn or passkeys and MUST support multi-factor authentication.
- **SEC-1.2** Session tokens MUST be stored in HttpOnly, Secure, SameSite cookies. Session identifiers and bearer tokens MUST NOT be placed in script-accessible storage.
- **SEC-1.3** Sessions MUST have idle and absolute lifetimes and MUST be revocable server-side.

### 8.2 Authorization and tenant isolation

- **SEC-2.1** Every request MUST be authorized per request against the authenticated user. There MUST be no implicit trust based on prior authentication or network position.
- **SEC-2.2** All data access MUST be scoped to the owning user. A user MUST NOT be able to read or modify another user's contacts under any code path. Verification: automated tests assert that cross-user access returns a not-found or forbidden response for every data endpoint.
- **SEC-2.3** Authorization decisions MUST fail closed. An indeterminate or errored policy decision MUST deny.

### 8.3 Token and secret management

- **SEC-3.1** OAuth tokens and provider credentials MUST be encrypted at rest using keys held in a managed key store. Application code MUST NOT have direct access to raw key material.
- **SEC-3.2** Secrets MUST NOT be committed to source control. A secret-scanning gate MUST run in CI.
- **SEC-3.3** Tokens MUST be revoked and purged on integration disconnect and on account erasure.

### 8.4 Input validation and output handling

- **SEC-4.1** All external input (user input, provider responses, webhook payloads) MUST be validated against an explicit schema and rejected on failure. Provider responses MUST NOT be trusted without validation.
- **SEC-4.2** All output rendered in any web context MUST be contextually encoded. The application MUST NOT construct HTML from untrusted strings.
- **SEC-4.3** Outreach URLs MUST be validated against the scheme allowlist in FR-6.4 before use.

### 8.5 Cryptography

- **SEC-5.1** All data in transit MUST use TLS 1.3. Plaintext transport MUST be rejected.
- **SEC-5.2** Restricted data at rest MUST be encrypted with AES-256-GCM or an equivalent authenticated cipher, with keys managed per SEC-3.1.
- **SEC-5.3** The system MUST be crypto agile. Algorithms and key references MUST be configurable and rotatable without code changes to callers.
- **SEC-5.4** For key establishment, where the platform and providers support it, the system SHOULD adopt hybrid post-quantum key exchange (for example, X25519 with ML-KEM-768 per FIPS 203). Long-lived stored secrets MUST be protected with rotation to enable migration to post-quantum algorithms.
- **SEC-5.5** The system MUST maintain a cryptographic inventory (algorithms, key lengths, key locations, rotation status) to support cryptographic asset management.
- **SEC-5.6** Backups, snapshots, and any other copies of Restricted data (including infrastructure-level volume or database snapshots) MUST be encrypted with the same authenticated cipher and managed keys as primary storage (SEC-5.2, SEC-3.1), MUST NOT store decryption keys alongside the ciphertext, and MUST be access-controlled and listed in the cryptographic inventory (SEC-5.5). Such copies are within the retention and purge schedule of PRIV-1.6 and the breach assessment of PRIV-1.14. This binds whatever backup mechanism is later chosen; until chosen, default to encrypted, key-separated backups (fail closed). Verification: a restored backup is unreadable without the managed key store, and a stored backup with no associated managed key is rejected rather than retained in plaintext.

### 8.6 Rate limiting and abuse prevention

- **SEC-6.1** Authentication, OAuth callback, DSR (including data access/export and erasure), contact-import, and reminder delivery endpoints MUST be rate limited. In addition, every authenticated endpoint MUST have a baseline per-user request-rate limit that is applied by default and fails closed (an endpoint with no explicit limit inherits the baseline rather than being unlimited). Operations that consume an external provider quota or are CPU/IO heavy — at minimum contact import (FR-1.5) and data export (PRIV-1.5) — MUST additionally be bounded by a per-user concurrency cap so a single user cannot exhaust shared provider quota or worker capacity. Verification: exceeding the configured request-rate or concurrency limit on each such endpoint returns 429 and enqueues no additional work, and an endpoint with no explicit policy is rejected at the baseline limit, not served unbounded.
- **SEC-6.2** The scheduler MUST cap reminders per user per window to prevent runaway delivery and notification flooding.
- **SEC-6.3** The system MUST enforce per-user resource quotas bounding the number of contacts and categories and the size of any single import batch, so that scheduler evaluation stays within its defined window (NFR-1.1) and no single account can exhaust shared storage or the import worker. Contact import MUST stream or paginate against the bound rather than load a provider address book wholesale. Exceeding a quota MUST fail closed: the create or import MUST be rejected with a field-level error and MUST NOT be silently truncated or partially written. Verification: a create or import request that would exceed the configured quota is rejected with no partial write, and the scheduler's per-window evaluation cost for any user remains bounded by the contact quota.

### 8.7 Webhook security

- **SEC-7.1** All inbound webhooks (SMS, WhatsApp, email provider) MUST verify provider signatures and reject unsigned or invalid requests. Replay MUST be mitigated with timestamp or nonce checks.

### 8.8 Audit logging

- **SEC-8.1** The system MUST produce tamper-evident audit logs (append-only or hash-chained) for, at minimum: authentication events, authorization denials, integration token use, consent grant and withdrawal (per channel and per optional processing), rectification of contact personal data, DSR actions, and all deletions. Each entry MUST record the acting principal, the action, the affected object identity, and a server-authoritative timestamp (client-supplied timestamps MUST NOT be trusted; see SEC-8.3). The audit write MUST be part of the same commit as the mutation it records: if the audit entry cannot be written, the mutation MUST fail closed and not be applied. NIST SP 800-53 AU controls apply. Verification: granting then withdrawing a channel consent produces two distinct, ordered, attributable audit entries, and a mutation whose audit write is forced to fail leaves no change persisted.
- **SEC-8.2** Audit logs MUST NOT contain secrets, tokens, or message content. Personal data in logs MUST be minimized and subject to retention.
- **SEC-8.3** The timestamp on every audit entry, consent record (PRIV-1.2), and security event MUST be assigned by a server-authoritative time source under the controller's control; a client-supplied time MUST NOT be trusted as the recorded time for these records, and an unavailable or unverifiable time source MUST fail closed (the record is rejected, not written with an untrusted time). Where the user may legitimately assert an event time (for example a backdated last-contact log per FR-4.1), the user-asserted event time and the immutable server record time MUST be stored as distinct fields; the record time, not the asserted time, is the basis for tamper-evidence under SEC-8.1 and for GDPR Article 5(2) accountability. Verification: a contact event or consent change submitted with a past or future user-asserted time records the true server time as the immutable record time, the asserted time is preserved in a separate field, and a record submitted while the authoritative time source is unavailable is rejected.
- **SEC-8.4** Audit-log retention MUST preserve tamper-evidence and MUST NOT delete or rewrite individual audit entries in a way that breaks the append-only or hash chain (SEC-8.1). Where audit entries are aged out by the retention job (PRIV-1.9), they MUST be removed only as sealed, independently verifiable segments, with the surviving chain re-anchored, and the purge MUST itself be recorded as a tamper-evident audit event. Security and DSR/accountability events (authentication, authorization denials, integration token use, consent changes, DSR actions, deletions) MUST be governed by a distinct accountability retention period, separate from and not shorter than operational-PII retention, sized to the accountability obligation. The purge MUST fail closed: if it cannot remove a segment while keeping the remaining chain verifiable, it MUST halt and alert rather than truncate or splice the chain. Verification: after a retention purge, an integrity check confirms the remaining audit chain still verifies end to end, the purge is itself logged as a tamper-evident entry, and security/DSR events within the accountability period are retained even if past operational-PII retention.
- **SEC-8.5** The integrity of the audit log MUST be independently verifiable and actively checked, not merely structurally tamper-evident. The system MUST (a) periodically verify the hash chain or append-only sequence end to end, (b) anchor the current chain head in a store separate from and not writable by the audit log's own write path, so an actor who rewrites records and recomputes downstream hashes is still detected, (c) segregate write access to audit storage from the application's normal data-access path, and (d) raise an alert on any detected break, gap, missing anchor, or out-of-order entry. Verification MUST fail closed: an unverifiable, broken, or unanchored chain MUST be treated as a tamper event and surfaced, never silently accepted. Verification: a test that mutates, reorders, or removes a historical entry (including tail truncation) causes the next integrity check to fail and emit an alert.

### 8.9 Dependency and supply chain

- **SEC-9.1** Third-party dependencies MUST be minimized. Each new dependency MUST be vetted for known CVEs, maintenance status, and transitive dependency footprint before introduction.
- **SEC-9.2** CI MUST run software composition analysis and static analysis. Builds MUST fail on newly introduced high-severity findings. See TEST-1.6 for the full CI-gate list.
- **SEC-9.3** A software bill of materials MUST be generated, and dependency versions MUST be pinned with integrity verification.

---

## 9. Frontend requirements (FE)

The frontend follows a secure-by-default React 19 posture: client only, function components and hooks only, no server-side rendering and no Node-specific APIs.

- **FE-1.1** `dangerouslySetInnerHTML` MUST NOT be used anywhere.
- **FE-1.2** All form input and all API response data MUST be validated with Zod before use.
- **FE-1.3** Every `href` and `src` MUST pass `validateAndSanitizeUrl`, returning `"#"` for any invalid or disallowed URL. This applies to all outreach deep links.
- **FE-1.4** The application MUST be CSP friendly: no inline event handlers, no inline script, no eval. A strict Content Security Policy MUST be enforced.
- **FE-1.5** Props MUST NOT be spread onto DOM nodes.
- **FE-1.6** React keys MUST be generated with `crypto.randomUUID` where a stable domain id is not available. Array index keys MUST NOT be used for dynamic lists.
- **FE-1.7** Data fetching in `useEffect` MUST guard against race conditions with an `AbortController` or an ignore flag, and MUST clean up on unmount.
- **FE-1.8** Any external script MUST use Subresource Integrity.

---

## 10. Non-functional requirements (NFR)

- **NFR-1.1** Reminder evaluation for a single user's contacts MUST complete within a defined scheduler window and MUST be horizontally scalable across users.
- **NFR-1.2** The reminder delivery path SHOULD achieve at least 99.5 percent successful delivery on healthy channels, with retries and dead-letter handling.
- **NFR-1.3** The system MUST emit operational metrics and structured logs free of personal data.
- **NFR-1.4** The UI MUST meet WCAG 2.2 AA.
- **NFR-1.5** Delivery-path retries (NFR-1.2) MUST be bounded and MUST NOT amplify a provider failure. Each reminder MUST have a maximum delivery-attempt count; retries MUST use exponential backoff with jitter. A per-channel circuit breaker MUST suspend sends to a channel after a configured consecutive-failure threshold and fail closed (no further attempts on that channel until reset) rather than retrying continuously. Messages whose attempts are exhausted MUST move to a dead-letter store of bounded size and retention; DLQ saturation MUST raise an operational alert and MUST NOT silently drop a reminder. This is delivery-path retry control and is distinct from the per-user generation cap (SEC-6.2). Verification: a simulated sustained provider outage trips the breaker, produces no unbounded retry or DLQ growth, and does not exhaust worker or queue capacity for other users.
- **NFR-1.6** Calls to critical external dependencies (the managed key store, the datastore, the reminder queue, and delivery providers) MUST be made through bounded timeouts and a circuit breaker, with bounded (non-infinite) retry. A transient dependency outage MUST fail closed for any security or privacy decision (it MUST NOT degrade into a weaker path; see SEC-2.3, SEC-3.1) but MUST be contained so a single dependency hiccup does not silently retry without bound or escalate into an unbounded, system-wide outage; non-security read paths MAY degrade gracefully (for example read-only or cached non-Restricted views) where doing so does not expose or weaken protection of Restricted data. Any in-memory retention of decrypted key material to absorb a transient key-store outage is a security decision owned by SECURITY.md §5 / SEC-3.1 and MUST NOT be introduced under this requirement. Verification: an injected key-store or datastore timeout returns a bounded, least-information error within the configured timeout, trips the breaker rather than exhausting the dependency with unbounded retries, and never serves Restricted data or an authorization/consent decision from a failed-closed path.

---

## 11. Testing and verification (TEST)

- **TEST-1.1** Automated test coverage MUST be at least 80 percent of statements, enforced as a CI gate.
- **TEST-1.2** The suite MUST include unit, integration, and end-to-end tests.
- **TEST-1.3** Security test cases MUST cover cross-user authorization isolation (SEC-2.2), redirect URI exact matching (INT-1.2), outreach URL scheme rejection (FR-6.4), token non-exposure (INT-1.6), and webhook signature rejection (SEC-7.1).
- **TEST-1.4** Privacy test cases MUST cover erasure cascade (PRIV-1.6), export completeness (PRIV-1.5), consent fail-closed delivery (FR-6.2), and retention expiry (PRIV-1.9).
- **TEST-1.5** Reminder engine tests MUST cover idempotency (FR-5.2), cadence boundary conditions, and quiet hours and timezone fail closed (FR-3.3).
- **TEST-1.6** CI MUST run SAST, SCA, secret scanning, and dependency checks, and MUST block merge on failure or on newly introduced high-severity findings.

---

## 12. Future AI features and required controls

If LLM-assisted features are added later (for example, drafting outreach text), the following MUST apply before launch, aligned to OWASP AISVS:

- The LLM MUST NOT be granted authority to send messages or mutate data directly. It produces draft text only, surfaced to the user for review.
- All prompt construction MUST treat contact data and any external content as untrusted, with prompt-injection screening on inputs.
- All model output MUST be validated and encoded before rendering, and MUST NOT be executed or used to construct URLs without passing FR-6.4 validation.
- Any tool or function exposed to the model MUST be least privilege, schema validated, and fail closed.

---

## 13. Standards traceability

- OAuth and identity: INT-1.x to RFC 9700, RFC 6749, RFC 9068.
- Zero Trust: SEC-2.x and overall architecture to NIST SP 800-207.
- Security controls and audit: SEC-8.x to NIST SP 800-53 Rev. 5 (AU, AC, IA, SC families).
- Privacy: PRIV-1.x to Regulation (EU) 2016/679, Articles 5, 6, 13–21, 25, 30, 32–35.
- Cryptography: SEC-5.x to NIST FIPS 203 and TLS 1.3 (RFC 8446).
- Application security and validation: FR and FE input handling to OWASP ASVS and the OWASP Cheat Sheet Series.
- Future AI: Section 12 to OWASP AISVS.

---

## 14. Open questions and risks

Resolved decisions are recorded inline in the relevant requirements and in ARCHITECTURE.md; the items below are what remains open or deferred.

**Still open / deferred (kept visible):**

- **Lawful basis & DPIA — confirmed position, advisor sign-off still required.** The lawful basis is confirmed as legitimate interests (Art. 6(1)(f)) for contact personal data with a documented LIA, and contract (Art. 6(1)(b)) for account data (PRIV-1.1). The household activity exemption (Article 2(2)(c)) may shield an end user's purely personal use but does not exempt the controller/processor operating the service. The DPIA, LIA, and lawful-basis position MUST still be reviewed and signed off by a qualified data protection advisor **before production launch** — this is a standing human gate, not yet cleared.
- **Direct third-party (contact) erasure beyond controller-mediated.** MVP is resolved to controller-mediated erasure plus a documented manual DSR process (PRIV-1.4). Any future direct, identity-verified third-party erasure spanning one or more users' data sets — intake, identity verification, and cross-user purge scope — remains open and requires DPO/legal sign-off before implementation.
- **Hosting cloud, region, and data residency — deferred.** Intentionally kept cloud-agnostic for now (see ARCHITECTURE.md). All infrastructure stays behind interfaces defaulting to the most restrictive option. This blocks finalizing processor Data Processing Agreements and the cross-border transfer mechanism (PRIV-1.12); both MUST be resolved before production launch.
- **SMS provider — deferred.** SMS delivery is in MVP scope (INT-5.1) but the concrete provider is undecided and kept behind the delivery interface; the webhook signature-verification contract is enforced regardless of provider.
- **Deferred infrastructure (behind interfaces, default-deny):** managed KMS vendor, durable queue/broker, transactional email provider, audit-chain external anchor store, container orchestrator, and the operational alerting destination. Each is tracked as a decision/issue and MUST be resolved with human sign-off before the dependent code path goes to production.
- **Brand finalization (non-blocking):** exact brand hex values require a color-pick against vector source art before production; font set is resolved to self-hosted open-source faces (Cinzel, Playfair Display, Inter, Poppins).

**Resolved (for reference):**

- **Delivery channels.** SMS, WhatsApp, and Signal delivery are promoted into MVP (FR-6.1, INT-5.x). WhatsApp requires in-WhatsApp opt-in and respects Cloud API session/template constraints; Signal is a self-hosted, best-effort, not-officially-supported channel, off by default.
- **Contact providers.** Google People, Microsoft Graph, CardDAV, and Apple Contacts (iCloud CardDAV) are all in MVP (FR-1.5, INT-4.1).
- **Calendar.** Read-only free/busy from Google Calendar is in MVP; event creation is later phase (INT-3.x).
- **Mailbox detection.** Gmail metadata-only, opt-in, default off, is in MVP (FR-4.3/4.4); DPIA/LIA records the added residual risk.
- **Database:** PostgreSQL (behind a repository interface). **Push:** standard Web Push with the application's own VAPID keys + RFC 8291 payload encryption. **Post-quantum:** migration-ready classical baseline (TLS 1.3 + crypto-agility + rotation). **Session store:** PostgreSQL-backed, server-side revocable. **CI:** GitHub Actions + OSS scanners behind a provider-agnostic definition. **SBOM:** CycloneDX. **Container base:** official slim, digest-pinned, non-root.
