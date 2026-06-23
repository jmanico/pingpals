# Requirement: MVP — Google Calendar read-only for meeting-aware cadence (event creation later)

## Metadata
- **ID**: REQ-MVP-077
- **Title**: Google Calendar read-only (free/busy) for meeting-aware cadence in MVP; event creation later phase
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Medium
- **Classification**: Functional
- **Decision**: **PARTIALLY PROMOTED INTO MVP.** **Google Calendar READ-ONLY (free/busy)** for meeting-aware cadence is now in MVP scope. **Calendar EVENT CREATION remains later-phase** (residual remainder), as does any non-Google calendar provider.

## Requirement
- **Description**: **PROMOTED INTO MVP (read-only).** The system integrates **Google Calendar read-only**, limited to **free/busy** (or the minimal event metadata necessary) for meeting-aware cadence, storing no event content beyond what is required (`INT-3.1`). **Calendar EVENT CREATION remains a later phase** (REQUIREMENTS.md §2.2): when implemented, any created event MUST be clearly attributed to Pingpals and deletable by the user (`INT-3.2`). Any inbound webhook used MUST verify provider signatures with replay mitigation (`SEC-7.1`). This issue MUST be decomposed into granular sub-issues when scheduled; it produces no code itself.
- **Rationale**: The project owner has **promoted Google Calendar read-only (free/busy) for meeting-aware cadence into MVP**; calendar event creation stays later-phase per §2.2. `INT-3.1` bounds calendar read to free/busy or required event metadata and forbids storing surplus event content; `INT-3.2` requires created events be attributed and deletable. This expands the OAuth and (optionally) webhook surface and must reuse the least-privilege, validated, revocable integration pattern.
- **Design**: Per `DESIGN.md`, meeting-aware cadence and any Pingpals-created event copy follow the regal/playful voice and design tokens; this issue tracks scope, not detailed UI.

## Scope
- **Applies To**: Both
- **Components**: OAuth provider adapter (022), scheduler/cadence (031/027 — meeting-aware adjustment), webhook security framework (if push-style calendar notifications are used; pattern from `SEC-7.1`), KMS token storage (011).
- **Actors**: Authenticated owning user connecting a calendar provider.
- **Data Classification**: Restricted (calendar metadata can reveal personal/relationship data; provider tokens).

## Security Context
- **Defense Layer**: Architecture / Input Validation.
- **Threat(s) Addressed**: Over-broad calendar scope / surplus event-content storage (CWE-272/data minimization), calendar-response injection (`SEC-4.1`), forged calendar push webhooks (CWE-345, mitigated by `SEC-7.1`). STRIDE: Elevation of Privilege, Information Disclosure, Spoofing.
- **Trust Boundary**: The calendar integration adapter (isolated, revocable) and, if used, the inbound calendar-webhook boundary (signature-verified).
- **Zero Trust Consideration**: Calendar responses and any webhook callbacks are untrusted until validated/verified; the adapter declares a pinned least-privilege (free/busy or minimal-metadata) scope and fails closed on broader requests (SECURITY.md §2); webhooks reject unsigned/replayed requests (`SEC-7.1`).

## Standards Alignment
- **OWASP ASVS**: V5.x (validation), V4.x (access control), V13/V14 (API/webhook)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: AC-6 (least privilege), SI-10 (input validation), SC-8 (webhook integrity)
- **NIST SP 800-207**: least-privilege scope; verify internal/external callbacks
- **Regulatory**: GDPR Art. 5(1)(c) minimization (no surplus event content), Art. 25 (privacy by default)
- **Other**: §2.2, `INT-3.1`, `INT-3.2`, `SEC-7.1`, `INT-1.1`–`INT-1.3` (OAuth baseline), `SEC-4.1`

## Acceptance Criteria
1. **AC-01**: Given scheduling, when this issue is picked up, then it is decomposed into granular sub-issues — **Google Calendar read-only / free-busy (MVP)**, **event creation (later-phase remainder)**, and calendar-webhook security — each citing governing tags.
2. **AC-02**: Given calendar read, when authorized, then the scope is limited to free/busy or the event metadata necessary for meeting-aware cadence, and event content beyond what is required is not stored. *(verbatim intent of `INT-3.1`.)*
3. **AC-03 (later-phase remainder)**: Given an event the system creates (event creation is later-phase, not MVP), when shown, then it is clearly attributed to Pingpals and is deletable by the user. *(verbatim intent of `INT-3.2`.)*
4. **AC-04 (negative)**: Given any inbound calendar webhook, when received unsigned, with an invalid signature, or replayed, then it is rejected and produces no processing (`SEC-7.1`).
5. **AC-05 (negative)**: Given a calendar response containing more than the required metadata, when processed, then surplus content is not stored (minimization), and the integration is independently revocable with token purge (`INT-1.7`, `SEC-3.3`).

## Failure Behavior
- **On Invalid Input**: Reject calendar responses/webhooks that fail schema/signature; store no surplus content.
- **On System Error**: Fail closed — a calendar/token error disables meeting-aware adjustment for that user without weakening cadence defaults or leaking data.
- **Alerting**: Repeated webhook signature failures or auth errors raise an operational signal.

## Test Strategy
- **Unit Tests**: Free/busy and minimal-metadata schema validation; surplus-content rejection; event-attribution/deletability builder; webhook signature + replay window.
- **Integration Tests**: Connect → read → meeting-aware cadence adjustment → revoke; create event → assert attribution + deletion; webhook receiver with forged/unsigned/replayed payloads.
- **Security Tests**: Attempt a broadened calendar scope (must fail closed); reuse 066 webhook-rejection and token-non-exposure patterns.
- **Compliance Tests**: Confirm no surplus event content is stored (`INT-3.1`); confirm a DPA exists for the calendar processor (`PRIV-1.12`).
- **Coverage Target**: ≥80% branch coverage per calendar adapter module when implemented.

## Dependencies
- **Upstream**: 022 (OAuth adapter), 027/031 (cadence/scheduler — meeting-aware adjustment), 011 (token encryption), 066 (webhook-security test patterns), decision 073 (region/DPA for the calendar processor).
- **Downstream**: Meeting-aware cadence refinements to the scheduler (031); 066 extends webhook tests to calendar callbacks.
- **External**: Calendar providers (Google/Microsoft); each requires `SEC-9.1` vetting and a DPA (`PRIV-1.12`).

## Implementation Notes
- **Constraints**: MVP scope is **Google Calendar read-only (free/busy)**; **event creation stays later-phase**. Decompose when scheduled. Prefer free/busy over full event metadata where it satisfies meeting-aware cadence (stronger minimization). Reuse the inbound-webhook signature pattern (`SEC-7.1`) for any calendar push notifications.
- **Anti-Patterns**: MUST NOT store event content beyond what is required (`INT-3.1`); MUST NOT create unattributed or non-deletable events (`INT-3.2`); MUST NOT process unsigned/replayed webhooks; MUST NOT request a broad full-calendar scope when free/busy suffices.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Calendar integration over well-documented provider APIs and the existing webhook/OAuth patterns is breadth-of-integration work; per-sub-issue human review enforces minimization (free/busy vs. metadata) and webhook security. Decompose before implementing.
