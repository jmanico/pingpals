# Requirement: Sending-domain anti-spoofing — SPF + DKIM + DMARC p=reject with alignment

## Metadata
- **ID**: REQ-DEL-039
- **Title**: SPF published, all reminder mail DKIM-signed, DMARC p=reject with SPF/DKIM identifier alignment
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Security

## Requirement
- **Description**: The domain used to send reminder email to the user MUST be protected against sender spoofing so recipients can authenticate that the mail originates from Pingpals. **SPF MUST be published**, **all reminder mail MUST be DKIM-signed**, and the sending domain MUST publish a **DMARC policy of `p=reject`** with SPF and DKIM **identifier alignment**. A reminder-only domain has no legitimate third-party senders, so `reject` is the fail-closed default; `quarantine` MAY be used only as a temporary, time-boxed rollout step. The configuration MUST be verifiable by an automated test that asserts the DNS records and confirms aligned, signed mail authenticates while unaligned/unsigned mail claiming the domain fails DMARC.
- **Rationale**: Reminder mail names a real contact and prompts the user to take action; a spoofed "Pingpals" email is a phishing vector against the user. SPF+DKIM+DMARC `p=reject` with alignment is the standard, fail-closed defense and is required by `INT-2.3`. Because the domain sends only reminders, there is no legitimate-third-party-sender reason to soften the policy below `reject`.
- **Design**: Brand presentation of the email (`DESIGN.md` §2.1) is unaffected by these DNS/auth controls; the `From:` domain and DKIM `d=` MUST align with the brand sending domain so the visible sender matches the authenticated identity.

## Scope
- **Applies To**: API / Backend (sending configuration) + Infrastructure (DNS)
- **Components**: Sending-domain DNS (SPF/DKIM/DMARC records); email adapter (038) DKIM signing config; a CI/operational verification test (TEST-1.6 evidence).
- **Actors**: Authenticated user (recipient/mail receiver); transactional email provider (signing on behalf of the domain).
- **Data Classification**: Internal (DNS records, selectors); Confidential (DKIM private key, held by/with the provider per its model).

## Security Context
- **Defense Layer**: Architecture (email authentication) — sender authenticity at the receiving boundary
- **Threat(s) Addressed**: Email spoofing / brand impersonation / phishing (CWE-290 authentication bypass by spoofing, OWASP A07:2021). STRIDE: Spoofing.
- **Trust Boundary**: The receiving mail server's DMARC evaluation boundary; an unaligned/unsigned message claiming the Pingpals domain is rejected there.
- **Zero Trust Consideration**: Receivers do not trust the `From:` header on assertion; authenticity is proven cryptographically (DKIM) and by authorized-sender policy (SPF) with DMARC alignment — anything else fails closed at the receiver.

## Standards Alignment
- **OWASP ASVS**: V14.4 (HTTP/transport & messaging security posture) / messaging authenticity guidance
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SC-8 (transmission integrity), SI-8 (spam/spoof protection)
- **NIST SP 800-207**: n/a
- **Regulatory**: GDPR Art. 5(1)(f) integrity (indirect — anti-phishing of data-subject prompts)
- **Other**: `INT-2.3`, RFC 7208 (SPF), RFC 6376 (DKIM), RFC 7489 (DMARC), NIST SP 800-177 (Trustworthy Email)

## Acceptance Criteria
1. **AC-01**: Given the sending domain, when its DNS is queried, then a valid SPF record, a DKIM selector/public key, and a DMARC record with `p=reject` and SPF+DKIM alignment are present.
2. **AC-02 (verbatim `INT-2.3`)**: Given legitimate reminder mail, when received, then it passes SPF and DKIM with DMARC alignment.
3. **AC-03 (verbatim `INT-2.3`, negative)**: Given mail from an unaligned or unsigned source claiming the Pingpals sending domain, when received by a conformant receiver, then it fails DMARC and is rejected.
4. **AC-04 (negative)**: Given a proposed configuration with `p=none`, or DKIM signing disabled for reminder mail, when validated, then the verification test fails (the rollout-only `quarantine` step is allowed solely as a time-boxed exception with an explicit expiry).
5. **AC-05**: Given all reminder mail sent by the adapter (038), when inspected, then every message is DKIM-signed (no unsigned reminder mail leaves the domain).

## Failure Behavior
- **On Invalid Input**: A reminder-mail send attempt from an unsigned/misaligned path is a configuration defect; the verification test fails the build.
- **On System Error**: Fail closed — absent or weaker-than-`reject` DMARC is treated as a failed control; the default and required steady-state is `p=reject`.
- **Alerting**: DMARC aggregate/forensic reports showing failing legitimate mail, or any drift away from `p=reject`, MUST raise an operational alert.

## Test Strategy
- **Unit Tests**: Record-builder/asserter parses and validates SPF/DKIM/DMARC record syntax and the `p=reject` + alignment requirement.
- **Integration Tests**: Send a real reminder through the adapter (038) to a test receiver and assert SPF/DKIM/DMARC pass with alignment; send a forged unaligned message and assert DMARC failure/rejection.
- **Security Tests**: Spoofing attempt from an unauthorized sender is rejected by a conformant receiver (maps to anti-phishing evidence).
- **Compliance Tests**: CI/operational check asserts live DNS records match the required policy (TEST-1.6 evidence); DMARC reporting endpoint configured.
- **Coverage Target**: ≥ 80% branch coverage of the record-verification module.

## Dependencies
- **Upstream**: 038 (email adapter — performs DKIM signing via the provider), hosting/DNS decision issue (sending domain & region).
- **Downstream**: end-to-end deliverability tests; brand/marketing sending hygiene.
- **External**: DNS provider; transactional email provider's DKIM signing; a conformant DMARC-evaluating receiver for tests.

## Implementation Notes
- **Constraints**: Sending domain and hosting region are tied to the hosting/region decision issue (`PRIV-1.12`, §14) — keep the domain/selector values in externalized config. The DKIM private key is a Confidential secret managed by/with the provider; it MUST NOT be committed (`SEC-3.2`). `quarantine` is permitted only as a temporary, expiry-bound rollout step before `reject`.
- **Anti-Patterns**: MUST NOT ship steady-state with `p=none`; MUST NOT send unsigned reminder mail; MUST NOT use a sending domain with legitimate third-party senders that would force a weaker policy; MUST NOT commit the DKIM private key.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Bounded DNS/email-auth configuration and a deterministic verification test against well-specified RFCs; mechanical and checklist-driven. Human review confirms steady-state `p=reject` with alignment and that no unsigned reminder path exists.
