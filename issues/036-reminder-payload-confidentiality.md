# Requirement: Minimal reminder payload + processor-traversal payload confidentiality

## Metadata
- **ID**: REQ-DEL-036
- **Title**: Minimal payload, and fail-closed confidentiality on processor-traversing / untrusted-surface channels
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Security

## Requirement
- **Description**: The reminder payload MUST contain only the data needed to act — contact display name, chosen channel, and the outreach action — and MUST NOT embed tokens, secrets, or unnecessary personal data. Where delivery traverses a third-party processor (transactional email, web push), the system MUST **fail closed on payload confidentiality**: if the channel supports application-layer payload encryption to the delivery endpoint (e.g. Web Push message encryption per RFC 8291), the system MUST use it so the processor cannot read contact personal data in cleartext; if the channel **cannot** encrypt end-to-end to the endpoint, **or** renders on an untrusted surface (push notification body, device lock screen), the delivered payload MUST NOT carry the contact display name or any other contact personal data — it MUST instead reference the reminder by an **opaque, non-guessable id** that reveals the contact only after an authenticated in-app fetch.
- **Rationale**: A reminder names a real third-party data subject (`§3`, Restricted). Transactional-email and web-push processors terminate transport TLS, and lock screens display content to anyone holding the device; cleartext PII there is a confidentiality breach (GDPR Art. 5(1)(f)) even though the transport was encrypted. This complements the minimal-payload rule `FR-5.4` and is the data-minimization counterpart to the endpoint/transport controls in issues 035, 037, and 040.
- **Design**: Per `DESIGN.md` §7, the reminder card shows the contact display name, chosen channel, and one outreach action only. On an untrusted-surface notification the user sees a neutral, PII-free prompt ("You have a royal reminder") that, when opened, performs an authenticated fetch and then renders the named card.

## Scope
- **Applies To**: API / Backend (payload builder) + Web App (in-app fetch on opaque id)
- **Components**: Reminder payload builder; delivery worker (035); email adapter (038); web-push adapter (040); opaque-reminder-id resolver endpoint; React reminder card.
- **Actors**: Authenticated user (recipient); third-party processors (email provider, push service) as untrusted intermediaries.
- **Data Classification**: Restricted (contact display name, outreach action); the opaque id is a non-PII reference.

## Security Context
- **Defense Layer**: Architecture (data minimization) + Encryption / Sanitization of payload
- **Threat(s) Addressed**: PII disclosure to a processor / on a lock screen (CWE-359, CWE-200), token/secret leakage in payload (CWE-522), reminder-id enumeration (CWE-639 if guessable). STRIDE: Information Disclosure.
- **Trust Boundary**: The send boundary to any third-party processor and the device-render surface. Both are outside the trust boundary; the payload is treated as readable by an untrusted party unless message-level encryption is applied to the endpoint.
- **Zero Trust Consideration**: Assumes transport TLS is insufficient because the processor terminates it; confidentiality is enforced at the message layer or by withholding PII entirely behind an authenticated fetch — never assumed from the transport.

## Standards Alignment
- **OWASP ASVS**: V8 (data protection), V6 (stored/processed sensitive data), V5.3 (output encoding for the in-app render)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SC-8 (transmission confidentiality), SC-28 (protection of information), AC-4 (information flow)
- **NIST SP 800-207**: untrusted-intermediary assumption
- **Regulatory**: GDPR Art. 5(1)(c) minimization, Art. 5(1)(f) confidentiality, Art. 25 privacy by default
- **Other**: `FR-5.4`, `FR-5.6`, RFC 8291 (Web Push message encryption), RFC 8030

## Acceptance Criteria
1. **AC-01**: Given an in-app/authenticated channel, when a reminder is delivered, then the payload contains only the contact display name, chosen channel, and outreach action — no tokens, secrets, or other personal data (`FR-5.4`).
2. **AC-02 (verbatim `FR-5.6`)**: Given a captured push or email payload, when inspected, then it contains no contact personal data in cleartext outside an encrypted body, and a payload on an unencryptable or lock-screen-rendered channel contains only an opaque reminder id.
3. **AC-03**: Given a channel that supports RFC 8291 message encryption to the endpoint, when a reminder is sent, then the contact display name is carried only inside the encrypted body and the processor cannot read it.
4. **AC-04 (negative)**: Given a channel that cannot apply message-level encryption and renders on an untrusted surface, when a reminder is sent, then the payload omits all contact PII and the contact is resolvable only via an authenticated in-app fetch of the opaque id.
5. **AC-05 (negative)**: Given an opaque reminder id, when fetched without the owner's authenticated session, then the fetch is denied and reveals no contact data (and ids are non-guessable / non-enumerable).

## Failure Behavior
- **On Invalid Input**: A payload that would carry PII onto an unencryptable/untrusted surface is rejected at build time; the opaque-id form is used instead.
- **On System Error**: Fail closed — if message-level encryption is required but cannot be applied, no PII-bearing payload is sent (the channel falls back to the opaque-id form or the send is suppressed per issue 040).
- **Alerting**: A build-time attempt to emit PII onto an untrusted-surface channel is a defect and SHOULD raise a developer/operational alert.

## Test Strategy
- **Unit Tests**: Payload builder includes only allowed fields; rejects tokens/secrets/extra PII; selects opaque-id form for untrusted-surface/unencryptable channels.
- **Integration Tests**: Capture an email and a push payload; assert no cleartext contact PII; assert encrypted-body path carries the name only inside ciphertext; opaque-id fetch requires auth.
- **Security Tests**: Attempt opaque-id enumeration and unauthenticated fetch (denied); inspect on-wire payloads with a capturing proxy (maps to TEST-1.4 confidentiality intent).
- **Compliance Tests**: Data-minimization audit confirms payload field set (`PRIV-1.7`).
- **Coverage Target**: ≥ 80% branch coverage of the payload-builder/resolver modules.

## Dependencies
- **Upstream**: 035 (owner/consent-verified delivery), 040 (web-push message encryption), 038 (email adapter), 014 (authz for the opaque-id fetch), 055/043 (outreach-link validation for any link in the payload).
- **Downstream**: 042 (delivery audit references the opaque reminder id), reminder card UI.
- **External**: Standard Web Push (provider-agnostic, DECISION 071 resolved); RFC 8291 encryption library subject to `SEC-9.x` vetting.

## Implementation Notes
- **Constraints**: Opaque reminder ids MUST be generated with a CSPRNG (non-guessable, non-enumerable) and resolve only within the owner's authenticated session. The payload builder is the single chokepoint; channel adapters consume its output and MUST NOT re-add PII. Push delivery uses standard Web Push (DECISION 071 resolved) — default to the opaque-id form behind the adapter interface until message-level encryption (RFC 8291) to the endpoint is confirmed.
- **Anti-Patterns**: MUST NOT rely on transport TLS for payload confidentiality across a processor; MUST NOT place contact PII in a lock-screen-rendered notification body; MUST NOT embed tokens/secrets in any payload; MUST NOT use a sequential or guessable reminder id.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Confidentiality-vs-usability trade-offs across untrusted surfaces require careful threat reasoning about where ciphertext ends and where PII can render; favor strong adversarial analysis. Human security review confirms no PII path bypasses the opaque-id form.
