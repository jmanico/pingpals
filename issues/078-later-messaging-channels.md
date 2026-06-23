# Requirement: MVP — SMS / WhatsApp / Signal reminder delivery to the user

## Metadata
- **ID**: REQ-MVP-078
- **Title**: Additional reminder-delivery channels to the user — SMS, WhatsApp, Signal (promoted into MVP)
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Medium
- **Classification**: Functional
- **Decision**: **PROMOTED INTO MVP.** SMS, WhatsApp, and Signal delivery to the user are now in MVP scope alongside email and in-app/push. **SMS:** concrete provider deferred behind a signature-verifying interface (`INT-5.1`). **WhatsApp:** enforce in-WhatsApp opt-in + Cloud API session/template constraints (`INT-5.2`); the concrete WhatsApp Business/Cloud API account is deferred. **Signal:** self-hosted signal-cli only, best-effort, NOT officially supported, **default OFF** (`INT-5.3`).

## Requirement
- **Description**: **PROMOTED INTO MVP.** The system delivers reminders to the user over **SMS, WhatsApp, and Signal** in addition to email and in-app/push. **SMS** delivery MUST verify inbound webhook signatures before processing any callback (`INT-5.1`, `SEC-7.1`); the concrete SMS provider is **deferred behind a signature-verifying interface**. **WhatsApp** delivery requires the user to have opted in within WhatsApp and MUST respect the Cloud API session and template constraints (`INT-5.2`); the concrete WhatsApp Business/Cloud API account is **deferred**. **Signal**, having no sanctioned multi-tenant sending API, MUST be a **self-hosted single-user signal-cli** integration, **best-effort**, **default OFF**, and MUST NOT be presented as an officially supported channel (`INT-5.3`). Per-channel affirmative consent (`FR-6.2`) applies to all three. This issue MUST be decomposed into granular per-channel sub-issues when scheduled; it produces no code itself.
- **Rationale**: The project owner has **promoted SMS/WhatsApp/Signal delivery to the user into MVP** (previously §2.2 later-phase) alongside the MVP email and in-app/push channels (`FR-6.1`). Each channel carries distinct security and terms-of-service constraints; the concrete SMS provider and WhatsApp Cloud API account are deferred behind interfaces, and Signal remains best-effort/unsupported and default-off.
- **Design**: Per `DESIGN.md`, channel selection and consent UI use design tokens and the gentle voice; Signal must be visibly labeled best-effort/unofficial, not on par with supported channels.

## Scope
- **Applies To**: Both
- **Components**: Delivery worker (035), channel-consent enforcement (034), delivery endpoint lifecycle (037), payload confidentiality (036), inbound webhook security (`SEC-7.1`), notification preferences (044).
- **Actors**: Authenticated owning user (recipient, consent grantor); SMS/WhatsApp providers; a self-hosted Signal sender.
- **Data Classification**: Restricted (delivery endpoints = phone numbers/handles; reminder payloads).

## Security Context
- **Defense Layer**: Architecture / Input Validation / Encoding.
- **Threat(s) Addressed**: Forged/replayed SMS delivery-status webhooks (CWE-345, `INT-5.1`/`SEC-7.1`), delivery without consent (unlawful processing, `FR-6.2`), PII exposure on untrusted channels/lock screens (`FR-5.6`), cross-user endpoint hijack (`FR-6.5`), misrepresenting an unsupported channel's reliability (Signal). STRIDE: Spoofing, Tampering, Information Disclosure, Repudiation.
- **Trust Boundary**: Each messaging provider is outside the trust boundary (TLS-terminating intermediary); inbound webhooks are a verified boundary (`SEC-7.1`); the self-hosted Signal integration is single-user infrastructure the user controls.
- **Zero Trust Consideration**: Provider webhooks are untrusted until signature/replay-verified; per-channel consent is evaluated per delivery and fails closed; delivery endpoints are ownership-bound and revocable (`FR-6.5`).

## Standards Alignment
- **OWASP ASVS**: V5.x (validation), V9.x (communications), V13/V14 (API/webhook)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SC-8 (transmission integrity), SI-10 (webhook validation), AC-3 (endpoint ownership)
- **NIST SP 800-207**: verify external callbacks; per-delivery consent decision
- **Regulatory**: GDPR Art. 6 (consent/lawful basis per channel), Art. 5(1)(c) minimization; provider ToS (WhatsApp Cloud API, Signal)
- **Other**: §2.2, §14, `INT-5.1`, `INT-5.2`, `INT-5.3`, `SEC-7.1`, `FR-6.1`, `FR-6.2`, `FR-6.5`, `FR-5.6`

## Acceptance Criteria
1. **AC-01**: Given MVP scheduling, when this issue is picked up, then it is decomposed into granular per-channel sub-issues (SMS, WhatsApp, Signal), each citing governing tags. The channels are in MVP scope, but the **concrete SMS provider** (behind the signature-verifying interface) and the **concrete WhatsApp Business/Cloud API account** are deferred and resolved with human sign-off before their build; **Signal defaults OFF** and stays unsupported/best-effort.
2. **AC-02 (SMS webhook)**: Given an inbound SMS provider webhook, when received unsigned, with an invalid signature, or replayed, then it is rejected and produces no processing. *(verbatim intent of `INT-5.1` / `SEC-7.1`.)*
3. **AC-03 (WhatsApp)**: Given WhatsApp delivery, when attempted, then it proceeds only if the user has opted in within WhatsApp and respects the Cloud API session/template constraints. *(verbatim intent of `INT-5.2`.)*
4. **AC-04 (Signal)**: Given Signal delivery, when offered, then it is implemented as a self-hosted single-user signal-cli integration, **default OFF**, labeled best-effort, and NOT presented as an officially supported channel. *(verbatim intent of `INT-5.3`.)*
5. **AC-05 (negative — consent)**: Given any of these channels without recorded affirmative consent, when a reminder is due, then no delivery occurs on that channel (`FR-6.2`); and the delivery endpoint is ownership-verified before send (`FR-6.5`).
6. **AC-06 (negative — payload)**: Given delivery on a channel that renders on an untrusted surface, when sent, then the payload carries no contact PII beyond what `FR-5.6` permits.

## Failure Behavior
- **On Invalid Input**: Reject unsigned/replayed provider webhooks; reject delivery on a non-consented or unverified-ownership channel.
- **On System Error**: Fail closed — a channel error skips that channel (no fallback that bypasses consent); circuit-breaker/retry per `NFR-1.5`.
- **Alerting**: Webhook signature failures, consent-absent delivery attempts, and channel circuit-breaker trips raise operational signals.

## Test Strategy
- **Unit Tests**: SMS webhook signature + replay window; WhatsApp session/template gate; Signal best-effort labeling; per-channel consent gate; endpoint ownership check.
- **Integration Tests**: Per-channel consent grant → delivery → withdrawal → no further delivery; SMS webhook with forged/unsigned/replayed payloads; WhatsApp opt-in precondition.
- **Security Tests**: Reuse 066 webhook-rejection and token-non-exposure patterns; attempt cross-user endpoint delivery (must be skipped); assert no PII on untrusted-surface payloads (`FR-5.6`).
- **Compliance Tests**: Confirm per-channel consent records (`PRIV-1.2`) and DPAs for SMS/WhatsApp providers (`PRIV-1.12`); confirm Signal ToS posture is documented.
- **Coverage Target**: ≥80% branch coverage per channel adapter module when implemented.

## Dependencies
- **Upstream**: 034 (channel-consent enforcement), 035 (delivery worker), 036 (payload confidentiality), 037 (endpoint lifecycle), 041 (retry/circuit-breaker), 044 (notification preferences), 066 (webhook test patterns), decision 070 (queue), decision 073 (region/DPA); §14 viability decision.
- **Downstream**: Notification preferences (044) gains new channel options; 066 extends webhook tests to SMS callbacks.
- **External**: SMS provider, WhatsApp Cloud API, self-hosted Signal (e.g. signal-cli on user-controlled infra); each requires `SEC-9.1` vetting, ToS review, and (for SMS/WhatsApp) a DPA.

## Implementation Notes
- **Constraints**: MVP-scope tracking — decompose per channel when scheduled. The channels are in MVP, but the **concrete SMS provider** and **WhatsApp Business/Cloud API account** are deferred behind interfaces and need human sign-off before their build; **Signal is self-hosted signal-cli, default OFF, best-effort, unsupported**. Reuse the MVP delivery-worker, consent, and endpoint-lifecycle machinery; do not bypass them per channel.
- **Anti-Patterns**: MUST NOT process unsigned/replayed SMS webhooks; MUST NOT deliver without per-channel consent (`FR-6.2`); MUST NOT present Signal as officially supported (`INT-5.3`); MUST NOT put contact PII on untrusted-surface payloads (`FR-5.6`); MUST NOT ignore WhatsApp session/template constraints (`INT-5.2`).
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Multi-provider messaging integration over documented APIs and existing webhook/consent/delivery patterns is breadth-of-integration work; the human gates are the §14 viability decision and per-sub-issue security/ToS review. Decompose and resolve viability before implementing.
