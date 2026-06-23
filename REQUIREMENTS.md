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
- Contact import from one provider (Google People API) at least-privilege scope.
- Relationship categorization with shipped defaults and user-defined categories.
- Per-category and per-contact cadence configuration.
- Manual last-contact logging.
- Reminder engine (cadence evaluation and scheduling).
- Reminder delivery to the user via email and in-app or push.
- One-tap outreach actions via validated deep links (mailto, tel, sms, WhatsApp click-to-chat, Signal).
- GDPR core: consent records, data export, erasure, retention enforcement.
- Security baseline per Section 8.

### 2.2 In scope (later phases)

- Additional contact providers (Microsoft Graph, CardDAV, Apple Contacts).
- Reminder delivery to the user via SMS, WhatsApp, and Signal.
- Calendar read for meeting-aware cadence, and optional calendar event creation.
- Opt-in automatic last-contact detection from mailbox metadata.

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
- **FR-1.5** Contact import MUST request the minimum provider scope required to read contacts and MUST NOT request write or send scopes during import.

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
- **FR-4.3** Automatic last-contact detection from mailbox metadata is later phase and MUST be opt-in per FR-4.4.
- **FR-4.4** If automatic detection is enabled, the system MUST request a read scope limited to message metadata (headers) only, MUST NOT read message bodies, and MUST allow the user to disable it and purge all derived data at any time.

### 5.5 Reminder engine

- **FR-5.1** The scheduler MUST generate a reminder for a contact when all of the following hold: now minus last contacted is greater than or equal to the effective cadence, the current time is within the allowed send window, the required channel consent is present, and no active snooze exists.
- **FR-5.2** Reminder generation MUST be idempotent. A single due event MUST NOT produce duplicate reminders. Verification: re-running the scheduler for the same window produces no additional reminders.
- **FR-5.3** The user MUST be able to snooze, dismiss, or mark a reminder as contacted. Mark as contacted MUST reset the cadence clock.
- **FR-5.4** The reminder payload MUST contain only the data needed to act (contact display name, chosen channel, outreach action). It MUST NOT embed tokens, secrets, or unnecessary personal data.

### 5.6 Multi-channel delivery

- **FR-6.1** The system MUST support delivery of the reminder to the user via email and in-app or push in MVP. SMS, WhatsApp, and Signal delivery to the user are later phase.
- **FR-6.2** For each enabled channel the system MUST hold an affirmative, recorded consent for that channel. Absence of consent MUST fail closed (no delivery on that channel).
- **FR-6.3** Each reminder MUST offer one or more outreach actions implemented as deep links: mailto, tel, sms, WhatsApp click-to-chat (`https://wa.me`), and Signal. The system MUST NOT transmit any message into these platforms itself.
- **FR-6.4** Every outreach URL MUST pass an allowlist-based URL validator before rendering. Allowed schemes: `mailto`, `tel`, `sms`, `https` (restricted to the click-to-chat host), and the Signal scheme. Any other scheme MUST be rejected and replaced with a safe fallback of `"#"`. Verification: a `javascript:` or `data:` scheme URL never reaches the DOM as an href.

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

### 6.2 Email integration

- **INT-2.1** MVP email delivery to the user MAY use a transactional email provider over an authenticated API. Provider credentials MUST be stored per Section 8.3.
- **INT-2.2** If a user mailbox is connected (later phase), scope MUST be limited to send for outreach assist, or metadata read for detection, and MUST NOT default to full mailbox read.

### 6.3 Calendar integration (later phase)

- **INT-3.1** Calendar read MUST be limited to free/busy or the event metadata necessary for meeting-aware cadence. Event content beyond what is required MUST NOT be stored.
- **INT-3.2** Any event the system creates MUST be clearly attributed to Pingpals and MUST be deletable by the user.

### 6.4 Contacts integration

- **INT-4.1** Contact read MUST use the provider contacts read scope only.
- **INT-4.2** Imported fields MUST be limited to name, phone, email, and a stable provider id for deduplication. The system MUST NOT import unrelated profile data.

### 6.5 Messaging delivery to the user (later phase)

- **INT-5.1** SMS delivery MUST verify inbound webhook signatures from the SMS provider before processing any callback.
- **INT-5.2** WhatsApp delivery to the user requires the user to have opted in within WhatsApp, and MUST respect the session and template message constraints of the WhatsApp Cloud API.
- **INT-5.3** Signal has no sanctioned multi-tenant sending API. Signal delivery, if implemented, MUST be treated as a self-hosted single-user integration (e.g. signal-cli on infrastructure the user controls), MUST be labeled best effort, and MUST NOT be presented as an officially supported channel (see §14).

---

## 7. Privacy and GDPR requirements (PRIV)

Pingpals processes personal data of third-party data subjects (the contacts) who are not users, creating obligations beyond ordinary account-data handling.

- **PRIV-1.1** The controller MUST document a lawful basis for processing contact personal data. The expected basis is legitimate interests under Article 6(1)(f), supported by a documented Legitimate Interests Assessment. User account data is processed under contract, Article 6(1)(b).
- **PRIV-1.2** The system MUST record explicit, granular, withdrawable consent from the user for each notification channel and for any optional processing (for example, automatic last-contact detection). Consent records MUST capture timestamp, scope, and notice version.
- **PRIV-1.3** The system MUST implement data subject rights for the user: access and portability (Articles 15 and 20), rectification (Article 16), erasure (Article 17), restriction (Article 18), and objection (Article 21).
- **PRIV-1.4** The system MUST provide a documented intake channel for data subject requests originating from a contact (a non-user). At minimum the controlling user MUST be able to erase a contact's data on request. The process for a direct third-party erasure request is recorded as an open decision in Section 14.
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

### 8.6 Rate limiting and abuse prevention

- **SEC-6.1** Authentication, OAuth callback, DSR, and reminder delivery endpoints MUST be rate limited.
- **SEC-6.2** The scheduler MUST cap reminders per user per window to prevent runaway delivery and notification flooding.

### 8.7 Webhook security

- **SEC-7.1** All inbound webhooks (SMS, WhatsApp, email provider) MUST verify provider signatures and reject unsigned or invalid requests. Replay MUST be mitigated with timestamp or nonce checks.

### 8.8 Audit logging

- **SEC-8.1** The system MUST produce tamper-evident audit logs (append-only or hash-chained) for authentication events, authorization denials, integration token use, DSR actions, and deletions. NIST SP 800-53 AU controls apply.
- **SEC-8.2** Audit logs MUST NOT contain secrets, tokens, or message content. Personal data in logs MUST be minimized and subject to retention.

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

- The household activity exemption (GDPR Article 2(2)(c)) may shield an end user's purely personal use, but it does not exempt the controller or processor operating the service. The lawful basis and the third-party data subject question require a DPIA and review by a qualified data protection advisor before launch.
- Direct erasure requests from a contact (a non-user), spanning the data sets of one or more users, are operationally hard. The intake process, identity verification, and the scope of any cross-user purge MUST be decided and documented. Recommendation: start with controller-mediated erasure (the user deletes the contact) plus a manual DSR process.
- Signal has no sanctioned sending API. Decide whether Signal as a delivery channel is worth the operational and terms-of-service cost, or whether it remains an outreach deep link only.
- WhatsApp Cloud API session and template constraints affect when a reminder can be delivered to the user. Confirm the opt-in flow before committing to WhatsApp delivery.
- Decide the hosting region and data residency to bound cross-border transfer obligations.
