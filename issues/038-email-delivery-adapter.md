# Requirement: MVP transactional-email delivery adapter (authenticated API, behind interface)

## Metadata
- **ID**: REQ-DEL-038
- **Title**: Send reminders to the user by email via a transactional provider over an authenticated API
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Functional

## Requirement
- **Description**: The system MUST support MVP delivery of the reminder to the user by **email**, sent via a transactional email provider over an **authenticated API**. The adapter MUST be implemented behind a provider-agnostic interface (the concrete provider is `TO BE DECIDED`). Provider credentials MUST be stored per SECURITY §5 — encrypted at rest with keys in the managed key store (issue 011), never committed to source or baked into images (`SEC-3.2`). The email payload MUST be the minimal payload of issue 036 (display name only where confidentiality permits), and the adapter MUST only be invoked for a reminder that has passed owner/consent re-verification (issue 035) to a verified, owned endpoint (issue 037).
- **Rationale**: Email is one of the two MVP delivery channels to the user (`FR-6.1`). A transactional API (vs. raw SMTP credentials) gives authenticated, observable sends and aligns with delivery audit (042) and anti-spoofing (039). Keeping the provider behind an interface honors the "many clouds / no premature infrastructure" posture and the `SEC-9.x` dependency-minimization rule.
- **Design**: Per `DESIGN.md` §2.1/§7, reminder email uses the horizontal lockup header and the brand voice (`DESIGN.md` §6); the body carries the contact display name, chosen channel, and the one validated outreach action (issue 043), nothing more.

## Scope
- **Applies To**: API / Backend (delivery worker channel adapter)
- **Components**: Email adapter (behind `EmailSender` interface); delivery worker (035); payload builder (036); credential store via KMS (011); outreach-link service (043); delivery audit (042).
- **Actors**: Authenticated user (recipient); transactional email provider (processor under a DPA, `PRIV-1.12`).
- **Data Classification**: Restricted (recipient address, contact display name, outreach action); Confidential (provider API credential).

## Security Context
- **Defense Layer**: Architecture (adapter isolation) + Secret handling
- **Threat(s) Addressed**: Credential leakage (CWE-522, CWE-798 hard-coded creds), PII over-disclosure in email body (handled by 036), provider lock-in / unvetted dependency (`SEC-9.1`). STRIDE: Information Disclosure, Tampering.
- **Trust Boundary**: API→email-provider send boundary; the provider is an untrusted processor (payload confidentiality per 036, sender authenticity per 039).
- **Zero Trust Consideration**: The adapter validates the provider's API response against an explicit schema (`SEC-4.1`) and never trusts a success acknowledgement without it; credentials are pulled from the KMS-backed store per send, never held in plaintext config.

## Standards Alignment
- **OWASP ASVS**: V6/V8 (secret & data protection), V5.1 (response validation)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SC-12/SC-28 (key & data protection), CM-6 (config), SA-9 (external services)
- **NIST SP 800-207**: n/a (functional adapter; security via 035/036/037/039)
- **Regulatory**: GDPR Art. 28 processor obligations / DPA (`PRIV-1.12`)
- **Other**: `INT-2.1`, `FR-6.1`, `SEC-3.1`, `SEC-3.2`, SECURITY §5

## Acceptance Criteria
1. **AC-01**: Given a reminder cleared by owner/consent re-verification (035) for the email channel to a verified owned address (037), when the adapter runs, then it sends the minimal payload (036) via the provider's authenticated API and records the outcome (042).
2. **AC-02**: Given provider credentials, when the adapter authenticates, then it retrieves them from the KMS-backed store at send time; the credential never appears in source, config files, images, logs, or audit entries.
3. **AC-03**: Given a different transactional provider is later selected, when swapped, then only the adapter implementation changes — the delivery worker and payload builder are unaffected (interface boundary holds).
4. **AC-04 (negative)**: Given the provider returns a malformed or error response, when received, then the adapter validates it against its schema, treats the send as not-delivered, and surfaces it to retry/DLQ (issue 041) rather than reporting success.
5. **AC-05 (negative)**: Given any code path, when inspected, then no provider credential is hard-coded or logged (secret-scanning gate, `SEC-3.2`).

## Failure Behavior
- **On Invalid Input**: A reminder not cleared by 035, or lacking a verified endpoint (037), is never handed to the adapter.
- **On System Error**: Fail closed for the security decision (no send without clearance); a provider/transport failure is a delivery failure routed to bounded retry / DLQ (issue 041), never a silent success.
- **Alerting**: Elevated provider-error or auth-failure rate raises an operational alert; credential-retrieval failure fails closed.

## Test Strategy
- **Unit Tests**: Adapter builds the request from the minimal payload; parses/validates provider responses; maps outcomes to delivered/retry/dead-lettered; no credential in any string.
- **Integration Tests**: End-to-end send through a stubbed provider; credential sourced from a mock KMS; outcome recorded via 042.
- **Security Tests**: Secret-scanning over the module (no hard-coded creds); response-injection fuzzing (malformed provider responses rejected).
- **Compliance Tests**: Confirm DPA-relevant config (region/provider) is externalized; payload field-set audit (036).
- **Coverage Target**: ≥ 80% branch coverage of the email adapter.

## Dependencies
- **Upstream**: 011 (KMS/credential encryption), 035 (owner/consent-verified delivery), 036 (minimal payload), 037 (endpoint lifecycle), 043 (outreach-link service), 041 (retry/DLQ), 042 (delivery audit).
- **Downstream**: 039 (anti-spoofing of the sending domain), end-to-end delivery tests.
- **External**: Transactional email provider (`TO BE DECIDED`, decision issue) under a DPA; managed KMS.

## Implementation Notes
- **Constraints**: Provider is `TO BE DECIDED` — code MUST keep the choice behind an `EmailSender` interface and default to a no-op/dev sink in non-production. Credentials are loaded from the KMS-backed store per `SEC-3.1`; rotate per `SEC-3.x`. New provider SDKs MUST be vetted per `SEC-9.1` and pinned with integrity (`SEC-9.3`).
- **Anti-Patterns**: MUST NOT hard-code or commit provider credentials; MUST NOT use unauthenticated SMTP; MUST NOT add contact PII beyond the minimal payload (036); MUST NOT report a send successful without a validated provider acknowledgement.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** A well-bounded adapter against established secret-handling, payload, and retry frameworks; mechanical integration work. Human review confirms no credential leakage and that the adapter consumes (not bypasses) 035/036/037.
