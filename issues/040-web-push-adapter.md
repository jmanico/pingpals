# Requirement: Web-push adapter — VAPID + RFC 8291 message encryption (fail closed)

## Metadata
- **ID**: REQ-DEL-040
- **Title**: Authenticated-sender (VAPID) + message-level encrypted/integrity-protected web push, or no push
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Security

## Requirement
- **Description**: The MVP in-app/push channel MUST deliver via web push using an **authenticated sender (VAPID, RFC 8292)** and **message-level encryption and integrity protection (RFC 8291 / RFC 8030)**, because the push intermediary terminates transport TLS and is outside the trust boundary — transport TLS alone is therefore insufficient. A push mechanism that **cannot** apply message-level protection MUST **fail closed**: no push delivery. The payload MUST be the confidentiality-aware minimal payload of issue 036 (PII only inside the encrypted body, else an opaque reminder id), and any outreach link carried in the payload remains subject to `FR-6.4` validation on render (issues 043/055). The push provider/mechanism is resolved to provider-agnostic standard Web Push with the app's own VAPID keys + RFC 8291 payload encryption (DECISION 071) and MUST be kept behind the adapter interface.
- **Rationale**: A push intermediary can read and alter anything not protected at the message layer; sending contact PII or an unauthenticated payload through it is a confidentiality/integrity breach (`FR-6.5`, `FR-5.6`). VAPID authenticates Pingpals as sender; RFC 8291 encrypts/authenticates the body to the subscription keys so the intermediary cannot read or tamper with it. Failing closed when message-level protection is unavailable preserves the privacy-by-default posture (`PRIV-1.13`).
- **Design**: Per `DESIGN.md` §5/§7, the push uses the speech-bubble/mascot-badge motif; on lock-screen/untrusted surfaces the visible text is the PII-free prompt from issue 036, with the named card revealed only after an authenticated in-app fetch.

## Scope
- **Applies To**: Both (backend push adapter + Web App service worker / subscription)
- **Components**: Web-push adapter (behind `PushSender` interface); VAPID keypair; RFC 8291 encryption; subscription registry (037); payload builder (036); outreach-link validation on render (043/055); delivery audit (042).
- **Actors**: Authenticated user (subscriber); push service (intermediary, untrusted relay).
- **Data Classification**: Restricted (subscription endpoint + p256dh/auth keys, encrypted payload); Confidential (VAPID private key).

## Security Context
- **Defense Layer**: Encryption + Authentication of sender (message-level, not transport)
- **Threat(s) Addressed**: Intermediary read of PII / payload tampering / spoofed push (CWE-300 MITM, CWE-319 cleartext, CWE-345 authenticity). STRIDE: Information Disclosure, Tampering, Spoofing.
- **Trust Boundary**: The push intermediary boundary — it terminates TLS and is assumed hostile; confidentiality and integrity are enforced at the message layer to the subscription keys.
- **Zero Trust Consideration**: The push service is never trusted with cleartext or with sender authority; every message is VAPID-authenticated and RFC 8291-encrypted/authenticated, and the path fails closed if either cannot be applied.

## Standards Alignment
- **OWASP ASVS**: V6 (cryptography at rest/in use), V8 (data protection), V14 (configuration)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SC-8 (transmission confidentiality/integrity), SC-12/SC-13 (key mgmt/crypto), SC-23 (session authenticity)
- **NIST SP 800-207**: untrusted-intermediary; message-level protection over transport trust
- **Regulatory**: GDPR Art. 5(1)(f) integrity & confidentiality, Art. 32 security of processing
- **Other**: `FR-6.5`, `FR-5.6`, `FR-6.4`, RFC 8291, RFC 8030, RFC 8292 (VAPID)

## Acceptance Criteria
1. **AC-01**: Given a verified, owned push subscription (037) and a cleared reminder (035), when the adapter sends, then the message is VAPID-authenticated and RFC 8291-encrypted to the subscription keys, and the outcome is audited (042).
2. **AC-02 (verbatim `FR-6.5`)**: Given a reminder pushed through an intermediary, when in transit, then it cannot be read or modified.
3. **AC-03 (verbatim `FR-5.6`)**: Given a captured push payload, when inspected, then it contains no contact personal data in cleartext outside the encrypted body, and on an unencryptable or lock-screen-rendered surface it contains only an opaque reminder id.
4. **AC-04 (negative, verbatim `FR-6.5` intent)**: Given a push mechanism that cannot apply message-level protection, when delivery is attempted, then push fails closed (no delivery) rather than sending a transport-TLS-only payload.
5. **AC-05 (negative)**: Given an outreach link in a push payload, when the client renders it, then it passes the `FR-6.4` allowlist validator (043/055) or renders as `"#"`.

## Failure Behavior
- **On Invalid Input**: A subscription that is unverified/foreign (037) receives nothing; a payload that would carry cleartext PII to an untrusted surface is downgraded to the opaque-id form (036).
- **On System Error**: Fail closed — if VAPID or RFC 8291 cannot be applied, no push is sent; a push-service transport failure is a delivery failure routed to retry/DLQ (issue 041).
- **Alerting**: Inability to apply message-level protection, or a spike in push-service rejections, MUST raise an operational/security alert.

## Test Strategy
- **Unit Tests**: VAPID JWT construction; RFC 8291 encryption to subscription keys; payload selection (encrypted body vs. opaque id); fail-closed when crypto unavailable.
- **Integration Tests**: End-to-end send to a stubbed push service; capture and attempt to read/modify the payload (must fail); opaque-id fetch requires auth (036).
- **Security Tests**: MITM/tamper simulation on the push body; spoofed-sender attempt without VAPID (rejected); outreach-link render passes 043/055 (maps to TEST-1.3 URL rejection).
- **Compliance Tests**: Crypto inventory lists the VAPID key and RFC 8291 usage (`SEC-5.5`); delivery audit recorded (042).
- **Coverage Target**: ≥ 80% branch coverage of the push adapter.

## Dependencies
- **Upstream**: 011 (KMS for VAPID/subscription key handling), 035 (cleared delivery), 036 (payload confidentiality), 037 (subscription lifecycle), 043/055 (outreach-link validation), 041 (retry/DLQ), 042 (delivery audit), **DECISION 071 (push provider/mechanism — resolved: standard Web Push + VAPID/RFC 8291)**.
- **Downstream**: end-to-end push delivery tests; reminder card / service worker.
- **External**: Browser Push API / push service; VAPID keypair; RFC 8291 crypto library (subject to `SEC-9.x` vetting and pinning).

## Implementation Notes
- **Constraints**: Push provider/mechanism is RESOLVED to provider-agnostic standard Web Push with the app's own VAPID keys + RFC 8291 — see **DECISION 071**; keep behind a `PushSender` interface and **default to no push** until VAPID + RFC 8291 are confirmed end to end. The VAPID private key is Confidential and KMS-managed (`SEC-3.1`); subscription keys are Restricted and encrypted at rest (011). Crypto MUST be agile/rotatable (`SEC-5.3`).
- **Anti-Patterns**: MUST NOT rely on transport TLS for confidentiality past the intermediary; MUST NOT send an unauthenticated (non-VAPID) push; MUST NOT carry cleartext PII to a lock-screen surface; MUST NOT render an unvalidated outreach link.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Message-level crypto over an untrusted intermediary with a hard fail-closed requirement is security-critical and error-prone; favor strong cryptographic and threat reasoning. Mandatory human security review; verify RFC 8291 encryption against known test vectors.
