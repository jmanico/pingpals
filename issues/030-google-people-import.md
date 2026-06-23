# Requirement: Google People contact import — least-scope, minimal fields, bounded streaming

## Metadata
- **ID**: REQ-CON-030
- **Title**: Import contacts from Google People (read-only scope, name/phone/email/provider-id only, paginated within quota)
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Medium
- **Classification**: Security

## Requirement
- **Description**: The system MUST import contacts from Google People using the provider's **contacts-read scope only** and MUST NOT request any write or send scope during import. Imported fields MUST be limited to display name, phone, email, and a stable provider id for deduplication; the system MUST NOT import unrelated profile data. Import MUST stream or paginate against the per-user quota bound (issue 029) rather than load the provider address book wholesale, MUST deduplicate by the stable provider id, and MUST be rate- and concurrency-limited (issue 013). Imported records MUST be validated against the same explicit contact schema and rejected on failure (reject over sanitize).
- **Rationale**: Least-privilege scope (`FR-1.5`, `INT-4.1`) and minimal imported fields (`INT-4.2`) enforce data minimization for third-party personal data. Streaming/paginating against the quota and applying rate/concurrency caps prevents a single user from exhausting the import worker or the shared Google quota (`SEC-6.1`/`SEC-6.3`).
- **Design**: Per `DESIGN.md` §6, the import flow is calm and explicit about exactly what is read (name, phone, email) and that nothing is written back to Google.

## Scope
- **Applies To**: Both
- **Components**: Flask API import endpoint + Google People integration adapter (built on OAuth adapter 022); per-user persistence (010); validation framework (009); quotas (029); rate/concurrency limiting (013).
- **Actors**: Authenticated user (owner); Google People API is an untrusted integration provider.
- **Data Classification**: Restricted (imported contact personal data; OAuth token in the adapter is Restricted).

## Security Context
- **Defense Layer**: Architecture (least-privilege scope, minimal fields) + Input Validation (provider response untrusted)
- **Threat(s) Addressed**: Over-broad OAuth scope / excessive data collection (CWE-272 least-privilege violation, OWASP API3 mass-assignment of provider fields), provider-response injection (CWE-20), import-worker/provider-quota exhaustion (CWE-770). STRIDE: Elevation of Privilege, Information Disclosure, Denial of Service.
- **Trust Boundary**: API↔Google integration edge; the provider response crosses into the trust boundary and is untrusted until validated. Token handling crosses into the KMS layer (011) only.
- **Zero Trust Consideration**: Google People responses are validated against an explicit schema and rejected on failure; the requested scope is verified against the adapter's pinned least-privilege declaration at request time and any out-of-set scope fails closed.

## Standards Alignment
- **OWASP ASVS**: V5.1 (input validation), V10/V51 (OAuth/least privilege), V8 (data minimization)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: AC-6 (least privilege), SI-10 (input validation), SC-5 (DoS protection)
- **NIST SP 800-207**: untrusted-input handling; per-request authorization
- **Regulatory**: GDPR Art. 5(1)(c) minimization, Art. 25 privacy by default, Art. 6(1)(f) lawful basis for contact data
- **Other**: `FR-1.5`, `INT-4.1`, `INT-4.2`, `SEC-6.1`, `SEC-6.3`, `SEC-4.1`, RFC 9700

## Acceptance Criteria
1. **AC-01**: Given an import, when the authorization request is built, then it requests the contacts-read scope only and no write/send scope (verified against the adapter's pinned least-privilege declaration; an out-of-set scope fails closed).
2. **AC-02**: Given a Google People response, when contacts are imported, then only display name, phone, email, and the stable provider id are stored; no unrelated profile data is persisted (`INT-4.2`).
3. **AC-03**: Given two import runs containing the same provider id, when imported, then the contact is deduplicated by provider id (no duplicate row).
4. **AC-04**: Given an address book larger than the import-batch bound, when imported, then the import streams/paginates against the quota (issue 029) and does not load it wholesale; an over-bound batch is rejected with no partial write.
5. **AC-05 (negative)**: Given a malformed or unexpected provider response field, when processed, then the affected record is rejected (reject over sanitize) and not coerced (`SEC-4.1`).
6. **AC-06 (negative)**: Given exceeded import rate or concurrency limits, when another import is attempted, then it returns 429 and enqueues no additional work (`SEC-6.1`).

## Failure Behavior
- **On Invalid Input**: Reject malformed provider records with no partial write; reject over-quota/over-rate with 409/429.
- **On System Error**: Fail closed — a scope mismatch, token-decrypt failure, or provider error aborts the import without partial persistence; OAuth/token handling follows 011/022.
- **Alerting**: Repeated provider-validation failures or quota exhaustion MAY raise an operational alert.

## Test Strategy
- **Unit Tests**: Scope-declaration enforcement; field allowlist (only name/phone/email/provider-id stored); dedup-by-provider-id; provider-response schema rejection.
- **Integration Tests**: Paginated import against the quota bound; dedup across runs; rate/concurrency limit enforcement (issue 013).
- **Security Tests**: Attempt to request a write/send scope (fail closed); inject malformed provider response (rejected); confirm token never appears in logs/URLs (`INT-1.6`).
- **Compliance Tests**: Schema audit confirms no unrelated profile fields persisted (`PRIV-1.7`); scope evidence for least-privilege.
- **Coverage Target**: ≥ 80% branch coverage of the import adapter + endpoint.

## Dependencies
- **Upstream**: 022 (OAuth provider adapter / token storage), 011 (KMS encryption at rest for tokens), 010 (persistence), 009 (validation), 013 (rate/concurrency), 029 (quota/batch bound), 024 (contact schema), 026 (category assignment on import).
- **Downstream**: 048 (account erasure purges imported provider tokens and data).
- **External**: Google People API (contacts-read scope) — vet per `SEC-9.x`; DPA required (`PRIV-1.12`).

## Implementation Notes
- **Constraints**: Adapter declares a pinned least-privilege scope set; the request is built from and verified against it (SECURITY §2). Streaming/pagination is mandatory — no wholesale address-book load. Tokens flow one way into the KMS layer (011); never to client/logs/URLs (`INT-1.6`). Per-user concurrency cap from issue 013. **MVP scope note**: the import framework now covers four contact providers in MVP — Google People (this issue), Microsoft Graph, CardDAV, and Apple Contacts (Apple = iCloud over CardDAV) — each behind its own adapter with a pinned contacts-read-only, least-privilege scope and the same minimal-field allowlist, dedup-by-provider-id, validation, and rate/concurrency bounds. This issue remains the Google People adapter; the sibling MS Graph / CardDAV / Apple-iCloud-CardDAV adapters are tracked separately but share this framework.
- **Anti-Patterns**: MUST NOT request write/send scope "for later"; MUST NOT import profile fields beyond the four; MUST NOT load the full address book into memory; MUST NOT trust provider responses without validation.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Combines OAuth least-privilege, untrusted-provider-response validation, dedup, and resource bounding — a security-dense integration where a scope or field-allowlist slip is a real privacy/exhaustion risk. Mandatory human security + privacy review before merge.
