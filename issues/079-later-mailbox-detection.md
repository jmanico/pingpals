# Requirement: MVP — opt-in automatic last-contact detection from Gmail metadata

## Metadata
- **ID**: REQ-MVP-079
- **Title**: Opt-in automatic last-contact detection from Gmail message metadata (promoted into MVP)
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Medium
- **Classification**: Privacy
- **Decision**: **PROMOTED INTO MVP — Gmail metadata only.** Uses the **`gmail.metadata` scope (headers only, never bodies)**, **opt-in, default OFF**, with **disable + purge of all derived data at any time**. The DPIA/LIA (issue 053, `PRIV-1.11`) MUST record the added residual risk. Additional mailbox providers (e.g. Microsoft Graph mail) **remain later-phase** (residual remainder).

## Requirement
- **Description**: **PROMOTED INTO MVP (Gmail only).** The system automatically detects last-contact events from **Gmail message metadata**, only when explicitly opted in. It MUST request the **`gmail.metadata` scope (headers only)**, MUST NOT read message bodies, and MUST allow the user to disable it and purge all derived data at any time (`FR-4.4`). The feature MUST be **off by default** (`PRIV-1.13`) and use a metadata-read scope only, never full-mailbox read (`INT-2.2`). The DPIA/LIA (issue 053, `PRIV-1.11`) MUST record the residual privacy risk this adds. **Additional mailbox providers (e.g. Microsoft Graph mail) remain later-phase.** This issue MUST be decomposed into granular sub-issues when scheduled; it produces no code itself.
- **Rationale**: The project owner has **promoted Gmail metadata-only last-contact detection into MVP** (previously a `FR-4.3`/`FR-4.4` later phase). `FR-4.4` bounds the scope to message-metadata headers, forbids body reads, and requires disable-and-purge. This is privacy-sensitive (mailbox metadata reveals communication patterns), so opt-in, privacy-by-default (`PRIV-1.13`), minimal scope (`INT-2.2`), and a DPIA/LIA residual-risk record (`PRIV-1.11`) are load-bearing.
- **Design**: Per `DESIGN.md`, the opt-in toggle and the disable/purge control use design tokens and the gentle voice, and the privacy-sensitive nature is clearly communicated; this issue tracks scope, not detailed UI.

## Scope
- **Applies To**: Both
- **Components**: OAuth provider adapter (022, mailbox metadata scope), last-contact logging (028, the detection feeds this), erasure/retention (048/051 for derived data purge), consent records (045), privacy-by-default (052), KMS token storage (011).
- **Actors**: Authenticated owning user (explicitly opts in / disables).
- **Data Classification**: Restricted (mailbox metadata and derived last-contact data are personal data; provider tokens).

## Security Context
- **Defense Layer**: Architecture / Privacy-by-default / Input Validation.
- **Threat(s) Addressed**: Over-broad mailbox scope or body reads (CWE-272, data minimization), processing without opt-in (unlawful processing, GDPR Art. 6), derived data persisting after disable (storage limitation), metadata-response injection (`SEC-4.1`). STRIDE: Information Disclosure, Elevation of Privilege, Repudiation.
- **Trust Boundary**: The mailbox integration adapter (isolated, revocable); the opt-in consent gate that authorizes any processing at all.
- **Zero Trust Consideration**: The feature processes nothing unless explicit, recorded opt-in consent exists; the adapter declares a pinned metadata-only scope and fails closed on any broader request (SECURITY.md §2); mailbox responses are validated before deriving last-contact events.

## Standards Alignment
- **OWASP ASVS**: V5.x (validation), V8.x (data protection), V4.x (access control)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: AC-6 (least privilege), SI-12 (data retention/disposal), AC-3 (per-user scoping)
- **NIST SP 800-207**: least-privilege scope; deny-by-default until opt-in
- **Regulatory**: GDPR Art. 6 (consent for optional processing), Art. 5(1)(c) minimization, Art. 5(1)(e) storage limitation, Art. 25 (privacy by default), Art. 7(3) (withdrawal as easy as grant)
- **Other**: `FR-4.3`, `FR-4.4`, `INT-2.2`, `PRIV-1.2`, `PRIV-1.13`, `PRIV-1.6`, `PRIV-1.9`

## Acceptance Criteria
1. **AC-01**: Given MVP scheduling, when this issue is picked up, then it is decomposed into granular sub-issues (Gmail-metadata adapter; detection logic feeding last-contact; opt-in/disable+purge; DPIA/LIA residual-risk record), each citing governing tags. Non-Gmail mailbox providers stay later-phase.
2. **AC-02**: Given the feature, when the account is provisioned, then it is off by default and processes nothing until explicit, recorded opt-in consent exists. *(maps to `PRIV-1.13` / `FR-4.3` / `PRIV-1.2`.)*
3. **AC-03**: Given detection is enabled, when authorized, then the scope is limited to message metadata (headers) only and message bodies are never read. *(verbatim intent of `FR-4.4` / `INT-2.2`.)*
4. **AC-04**: Given the user disables detection, when they do so, then all derived detection data is purged and processing stops. *(verbatim intent of `FR-4.4`; ties `PRIV-1.6`.)*
5. **AC-05 (negative)**: Given a flow requesting full-mailbox or body-read scope, when authorized, then it fails closed and does not proceed (`INT-2.2`, SECURITY.md §2); and without recorded opt-in consent, no mailbox processing occurs (fail closed).

## Failure Behavior
- **On Invalid Input**: Reject mailbox responses that fail schema validation; never parse bodies.
- **On System Error**: Fail closed — a token/scope error disables detection without falling back to a broader scope or body read; derived data remains purgeable.
- **Alerting**: Scope-broadening attempts or purge failures raise an operational/privacy signal.

## Test Strategy
- **Unit Tests**: Metadata-only scope declaration enforcement; header-parsing with body access blocked; derived-data purge on disable; opt-in consent gate (no processing without it).
- **Integration Tests**: Opt-in → detect last-contact → mark contact (feeds 028) → disable → assert derived data purged and processing stopped; assert default-off.
- **Security Tests**: Attempt a broadened/body-read scope (must fail closed); attempt processing without consent (must be denied); reuse 066 token-non-exposure patterns.
- **Compliance Tests**: Confirm consent records for the optional processing (`PRIV-1.2`), default-off (`PRIV-1.13`), purge-on-disable (`FR-4.4`/`PRIV-1.6`), and a DPA for the mailbox provider (`PRIV-1.12`); covered by the 067 privacy-suite patterns.
- **Coverage Target**: ≥80% branch coverage of the detection/adapter modules when implemented.

## Dependencies
- **Upstream**: 022 (OAuth adapter, metadata scope), 028 (last-contact logging — detection target), 045 (consent records), 048/051 (purge/retention of derived data), 052 (privacy-by-default), 011 (token encryption), decision 073 (region/DPA for the mailbox provider).
- **Downstream**: 028 (auto-detected events reset the cadence clock); 067 (privacy suite extends to derived-data purge).
- **External**: Mailbox provider metadata-read API (e.g. Gmail metadata scope); requires `SEC-9.1` vetting and a DPA (`PRIV-1.12`).

## Implementation Notes
- **Constraints**: MVP scope is **Gmail metadata-only** (`gmail.metadata`); other mailbox providers stay later-phase. Decompose when scheduled. The metadata-only scope and no-body-read rule are non-negotiable; default-off and disable+purge are mandatory; the DPIA/LIA (053) MUST record the added residual risk (`PRIV-1.11`). Treat derived last-contact data as Restricted under full erasure/retention controls.
- **Anti-Patterns**: MUST NOT request full-mailbox or body-read scope (`FR-4.4`, `INT-2.2`); MUST NOT process without explicit recorded opt-in (`FR-4.3`, `PRIV-1.2`); MUST NOT default the feature on (`PRIV-1.13`); MUST NOT retain derived data after disable (`FR-4.4`).
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Mailbox-metadata integration over a documented provider API with the established opt-in/least-scope/purge patterns is breadth-of-integration work; the human gate is privacy review of scope minimization (metadata-only, no bodies) and disable+purge completeness. Decompose before implementing.
