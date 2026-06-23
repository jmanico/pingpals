# Requirement: MVP — additional contact providers (Microsoft Graph, CardDAV, Apple Contacts)

## Metadata
- **ID**: REQ-MVP-076
- **Title**: Additional contact-import providers beyond Google People (promoted into MVP)
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Medium
- **Classification**: Functional
- **Decision**: **PROMOTED INTO MVP.** Microsoft Graph, CardDAV, and **Apple Contacts (realized as iCloud over CardDAV — no first-party Apple server API)** are now in MVP scope alongside Google People. All are **contacts-read least-privilege only**. CardDAV app-password credentials are transported over TLS and stored encrypted at rest. No further contact-provider remainders for MVP.

## Requirement
- **Description**: **PROMOTED INTO MVP.** In addition to Google People, the system supports **Microsoft Graph, CardDAV, and Apple Contacts** as contact-import providers in MVP. Apple Contacts is realized as **iCloud over CardDAV** (Apple exposes no first-party server contacts API). Each provider requests only the contacts-read least-privilege scope (`INT-4.1`), imports only the fields permitted by `INT-4.2`, and is independently revocable by the user (`INT-1.7`). CardDAV (including iCloud) uses **app-password credentials transported over TLS (`SEC-5.1`) and stored encrypted at rest** under the managed key store (`SEC-3.1`/`SEC-5.2`), not OAuth. This issue MUST be decomposed into granular per-provider sub-issues when scheduled; it produces no code itself.
- **Rationale**: Originally §2.2 later-phase, these providers have been **promoted into MVP** by the project owner alongside the Google People MVP importer (§2.1). Each added provider expands the OAuth/integration (and, for CardDAV, the stored-credential) attack surface and must reuse the same least-privilege, revocable, validated adapter pattern as the Google People adapter.
- **Design**: Per `DESIGN.md`, provider connect/disconnect UI uses design tokens and the same import affordances as Google People; this issue tracks scope, not detailed UI.

## Scope
- **Applies To**: Both
- **Components**: OAuth provider adapter (022), Google People import (030, the exemplar to generalize), contact CRUD (024), resource quotas (029), KMS token/credential storage (011 — includes encrypted CardDAV/iCloud app-password storage).
- **Actors**: Authenticated owning user connecting a contacts provider.
- **Data Classification**: Restricted (imported contact PII; provider tokens).

## Security Context
- **Defense Layer**: Architecture / Input Validation (each provider response is untrusted and validated).
- **Threat(s) Addressed**: Over-broad scope grants (CWE-272 least-privilege violation), provider-response injection (validate per `SEC-4.1`/`FR-1.4`), cross-provider token leakage (per-adapter decrypt partitioning, SECURITY.md §5), import-driven resource exhaustion (`SEC-6.3`). STRIDE: Elevation of Privilege, Tampering, Denial of Service.
- **Trust Boundary**: Each integration adapter is an isolated, independently-revocable boundary; revoking one MUST NOT affect another (`INT-1.7`, ARCH Rule 7).
- **Zero Trust Consideration**: Every provider response is validated against an explicit schema before storage; the adapter declares a pinned least-privilege scope and a flow requesting any scope outside it fails closed (SECURITY.md §2).

## Standards Alignment
- **OWASP ASVS**: V5.x (validation), V4.x (access control)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: AC-6 (least privilege), SI-10 (input validation), AC-3 (per-user scoping)
- **NIST SP 800-207**: least-privilege, per-request scoping per provider
- **Regulatory**: GDPR Art. 5(1)(c) data minimization (`INT-4.2` field limits), Art. 25 (privacy by default)
- **Other**: §2.2, `INT-4.1`, `INT-4.2`, `INT-1.7`, `INT-1.1`–`INT-1.3` (OAuth baseline), `SEC-6.3`

## Acceptance Criteria
1. **AC-01**: Given MVP scheduling, when this issue is picked up, then it is decomposed into granular per-provider sub-issues (Microsoft Graph, CardDAV, Apple Contacts via iCloud-over-CardDAV), each citing its governing tags.
2. **AC-02**: Given any provider adapter built from this track, when it requests authorization, then it requests only the contacts-read least-privilege scope and never a write/send scope during import. *(maps to `INT-4.1` / `FR-1.5`.)*
3. **AC-03**: Given an import, when fields are read, then only name, phone, email, and a stable provider id for deduplication are imported; unrelated profile data is not. *(verbatim intent of `INT-4.2`.)*
4. **AC-04 (negative)**: Given a connected provider, when the user revokes it, then its tokens are purged and revocation does not affect any other provider's tokens or imports (`INT-1.7`, `SEC-3.3`).
5. **AC-05 (negative)**: Given a provider response with unexpected/extra fields, when imported, then it is validated and rejected/ignored per schema (no mass-assignment), and an import exceeding the per-user quota fails closed with no partial write (`SEC-6.3`, `FR-1.4`).

## Failure Behavior
- **On Invalid Input**: Reject the provider response; do not coerce. Quota overflow returns a field-level error with no partial write (`SEC-6.3`).
- **On System Error**: Fail closed — a provider/token error aborts the import for that provider without affecting others or weakening scope.
- **Alerting**: Repeated provider auth failures or quota breaches raise an operational signal.

## Test Strategy
- **Unit Tests**: Per-provider response schema validation; scope-declaration enforcement; field-limit filter (`INT-4.2`); dedup via stable provider id.
- **Integration Tests**: Connect → import → revoke per provider; assert independent revocation and token purge; assert quota fail-closed.
- **Security Tests**: Attempt a broadened-scope authorization (must fail closed); attempt cross-provider token decrypt (must be denied, SECURITY.md §5); reuse the 066 security-suite patterns (redirect-URI exact match, token non-exposure).
- **Compliance Tests**: Confirm imported fields stay within `INT-4.2`; confirm a DPA exists for each new provider (`PRIV-1.12`).
- **Coverage Target**: ≥80% branch coverage per provider adapter module when implemented.

## Dependencies
- **Upstream**: 022 (OAuth adapter), 030 (Google People import — pattern to generalize), 011 (token encryption), 029 (resource quotas), decision 073 (region/DPA for new processors).
- **Downstream**: 024 (contact CRUD consumes imported contacts); 066 (security suite extends to new providers).
- **External**: Microsoft Graph, CardDAV servers, Apple Contacts APIs; each requires `SEC-9.1` dependency vetting and a DPA (`PRIV-1.12`).

## Implementation Notes
- **Constraints**: MVP-scope tracking — decompose into per-provider sub-issues when scheduled. Reuse the Google People adapter pattern; do not fork bespoke logic per provider. CardDAV and Apple Contacts (iCloud over CardDAV) use app-password credentials rather than OAuth — those creds MUST be transported over TLS (`SEC-5.1`) and stored encrypted at rest (`SEC-3.1`/`SEC-5.2`); each sub-issue MUST pin its own least-privilege scope and validation.
- **Anti-Patterns**: MUST NOT request write/send scopes during import (`FR-1.5`); MUST NOT import profile data beyond `INT-4.2`; MUST NOT couple providers so one's revocation affects another; MUST NOT trust provider responses without schema validation.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Generalizing a known least-privilege OAuth/import adapter pattern across additional well-documented providers is breadth-of-integration work; per-sub-issue security review (scope pinning, token partitioning) is the human gate. Decompose before implementing.
