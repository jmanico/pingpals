# Requirement: Hard-delete erasure cascade across all personal-data stores

## Metadata
- **ID**: REQ-PRIV-048
- **Title**: Transactional hard-delete erasure cascade with backup purge schedule
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Critical
- **Classification**: Compliance (security-significant: an incomplete cascade leaves orphaned Restricted PII)

## Requirement
- **Description**: Erasure MUST be a hard delete that cascades across contacts, reminders, outreach history, derived detection data, and provider tokens, so that no orphaned personal data remains. Deletion of a single contact MUST remove all associated personal data, reminders, and outreach history within the same transaction (`FR-1.3`). Account erasure MUST cascade across every store holding the subject's data (`ARCH` Dependency Rule 9). Backups, snapshots, and any other copies MUST be covered by a documented retention and purge schedule. After completion, a post-deletion query MUST return no personal data for the subject in primary storage. This requirement pairs with the surviving proof-of-erasure record defined in issue 049 (`PRIV-1.16`).
- **Rationale**: GDPR Article 17 (right to erasure) requires the controller to erase personal data without undue delay; a partial cascade that leaves reminders, outreach history, derived detection data, or provider tokens behind is a continuing unlawful processing and a breach exposure. Hard delete (not soft-delete flags) is mandated so the data is genuinely gone. This is the data-of-record behind `PRIV-1.6`, `FR-1.3`, and `ARCH` Rule 9.
- **Design**: Per `DESIGN.md` §6, the erasure confirmation uses the gentle royal voice but is explicit and irreversible; no styling depends on the cascade. The UI surfaces erasure as a DSR action (issue 050).

## Scope
- **Applies To**: Both
- **Components**: Privacy/DSR subsystem — erasure executor; spans all per-user-scoped repositories (010), provider-token store (011/022), reminder/outreach stores, derived detection store; backup purge policy.
- **Actors**: Authenticated user (owner) erasing their own contact or account; controller-mediated erasure of a contact on a non-user's behalf (intake per issue 050 / DECISION 075).
- **Data Classification**: Restricted/PII across all listed stores; provider tokens are Restricted (Confidential credentials material).

## Security Context
- **Defense Layer**: Architecture (transactional cascade across the trust boundary's stores)
- **Threat(s) Addressed**: Orphaned personal data after deletion (CWE-212 improper removal of sensitive information), partial-delete inconsistency, residual provider tokens granting continued access. STRIDE: Information Disclosure, Repudiation.
- **Trust Boundary**: API service / Persistence layer — the erasure executor is the single authority that reaches every store holding the subject's data; no component may retain a private copy outside the cascade.
- **Zero Trust Consideration**: The cascade enumerates stores explicitly rather than trusting that "the database cascade will handle it"; every store is treated as potentially holding orphaned data until proven empty by a post-deletion query.

## Standards Alignment
- **OWASP ASVS**: V8.x (data protection / retention & disposal)
- **OWASP AISVS**: n/a (no AI component)
- **NIST SP 800-53**: MP-6 (media sanitization), SI-12 (information handling/retention), AU-2 (audit of deletions)
- **NIST SP 800-207**: explicit, enumerated data-flow termination
- **Regulatory**: GDPR Arts. 17 (erasure), 5(1)(e) (storage limitation), 5(2) (accountability via 049)
- **Other**: `PRIV-1.6`, `FR-1.3`, `FR-1.2`, `SEC-3.3` (token purge), `SEC-5.6` (backups), `ARCH` Dependency Rule 9

## Acceptance Criteria
1. **AC-01 (verbatim `FR-1.3`)**: Given a contact is deleted, when the operation completes, then a post-deletion query returns no rows for that contact across all tables (associated personal data, reminders, and outreach history removed in the same transaction).
2. **AC-02 (verbatim `PRIV-1.6`)**: Given an erasure runs, when it completes, then an erasure test confirms no personal data for the subject remains in primary storage.
3. **AC-03**: Given an account/contact erasure, when it executes, then it cascades across contacts, reminders, outreach history, derived detection data, and provider tokens, and the tokens are revoked at the provider as well as purged locally (`SEC-3.3`).
4. **AC-04**: Given backups/snapshots exist, when the documented retention/purge schedule runs, then the subject's data in those copies is purged per schedule (`SEC-5.6`), and the schedule is documented (cross-ref 053 RoPA/DPIA).
5. **AC-05 (negative)**: Given any single store fails to delete during the cascade, when the transaction is evaluated, then the erasure is not reported complete (fail closed) and no partial/inconsistent state is left committed — coordinated with the proof-of-erasure gate in issue 049.

## Failure Behavior
- **On Invalid Input**: Reject an erasure request that cannot be resolved to a single owned subject with HTTP 422/404; no deletion performed.
- **On System Error**: Fail closed — if any store in the cascade cannot be confirmed purged, the erasure aborts and is not reported complete (it MUST NOT report success on a partial cascade); see issue 049 for the durable-proof gate.
- **Alerting**: A failed/aborted cascade or a residual-data finding raises an operational + compliance alert.

## Test Strategy
- **Unit Tests**: Per-store deletion logic; same-transaction guarantee for single-contact delete; token revoke+purge path.
- **Integration Tests**: Seed a subject across every store, erase, assert post-deletion queries return nothing across all tables and the provider token is revoked (maps to TEST-1.4 erasure cascade).
- **Security Tests**: Inject a mid-cascade store failure and assert no partial commit and no success report; assert no residual provider token usable after erasure.
- **Compliance Tests**: Automated residual-data scan over all stores post-erasure; documented backup purge schedule present (053).
- **Coverage Target**: ≥ 80% branch coverage of the erasure executor.

## Dependencies
- **Upstream**: 010 (per-user-scoped persistence), 011 (KMS / token store), 022 (provider-token adapter for revoke), 024 (contact model), 045 (consent records are within scope of the cascade), 012 (audit of deletions).
- **Downstream**: 049 (proof-of-erasure — gates completion), 050 (DSR endpoints invoke erasure), 047 (erasure removes outstanding export artifacts), 051 (retention job is the scheduled counterpart for backups/aged data).
- **External**: Provider token-revocation endpoints (Google People, transactional email); backup/snapshot store `TO BE DECIDED` (default encrypted, key-separated, on a documented purge schedule).

## Implementation Notes
- **Constraints**: Single-contact delete MUST be one transaction; account erasure cascades enumerate every store explicitly. Provider tokens revoked at source then purged. Backup purge schedule documented in 053 (RoPA/DPIA). `Split recommendation:` if the backup-purge tooling grows large, split it into a separate retention-tooling issue under 051.
- **Anti-Patterns**: MUST NOT use soft-delete flags as erasure; MUST NOT rely solely on an ORM cascade without verifying every enumerated store; MUST NOT report success on a partial cascade; MUST NOT leave a usable provider token after erasure.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** A correctness- and compliance-critical cascade where a missed store is a continuing GDPR breach; favor the strongest reasoning on transactional completeness and enumeration. Mandatory human privacy/security review before merge; keep the completion gate in lockstep with issue 049.
