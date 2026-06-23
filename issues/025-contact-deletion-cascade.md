# Requirement: Single-contact deletion cascade in one transaction

## Metadata
- **ID**: REQ-CON-025
- **Title**: Contact deletion removes all associated data, reminders, and outreach history atomically
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Privacy

## Requirement
- **Description**: Deletion of a contact MUST remove all associated personal data, reminders, and outreach history within the **same transaction**, such that a post-deletion query returns no rows for that contact across all tables. The operation MUST be atomic: either every associated row is removed and the deletion is recorded in the audit log, or nothing is removed.
- **Rationale**: Contacts are personal data of third-party data subjects (`§3`, Restricted). Leaving orphaned reminders, contact events, or outreach history after a contact delete violates data minimization and storage limitation (`PRIV-1.7`/`PRIV-1.9`) and breaks the controller-mediated erasure path that GDPR relies on (`PRIV-1.4`). Atomicity prevents a half-deleted contact that is invisible in the UI but retains personal data.
- **Design**: Per `DESIGN.md` §6, the delete confirmation is gentle but unambiguous; on success the contact and all its dependents disappear from every view.

## Scope
- **Applies To**: Both
- **Components**: Flask API contact-delete endpoint; per-user persistence (010); reminder/contact-event/outreach-history stores; audit log (012).
- **Actors**: Authenticated user (owner) deleting their own contact.
- **Data Classification**: Restricted (contact name, phone, email, notes; derived reminders, contact events, outreach history).

## Security Context
- **Defense Layer**: Architecture (transactional cascade + user-scoped enforcement)
- **Threat(s) Addressed**: Orphaned personal-data retention (CWE-212 improper removal of sensitive information), partial-delete inconsistency, cross-user deletion (OWASP API1:2023). STRIDE: Information Disclosure, Tampering.
- **Trust Boundary**: Client→API edge; the cascade executes server-side within a single DB transaction.
- **Zero Trust Consideration**: The delete is authorized per-request and scoped to the owning user; the contact id is treated as untrusted and resolved only within the user's data set (`SEC-2.2`).

## Standards Alignment
- **OWASP ASVS**: V13/V11 (object-level access control), V8 (data protection)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SI-12 (information management/retention), AU-12 (audit generation), AC-3
- **NIST SP 800-207**: per-request, user-scoped authorization
- **Regulatory**: GDPR Art. 5(1)(c)/(e) minimization & storage limitation, Art. 17 erasure (contact-level)
- **Other**: `FR-1.3`, `PRIV-1.4`, ARCH Dependency Rule 9

## Acceptance Criteria
1. **AC-01 (verbatim `FR-1.3`)**: When a contact is deleted, then a post-deletion query returns no rows for that contact across all tables (personal data, reminders, outreach history removed within the same transaction).
2. **AC-02**: Given a delete that fails midway (e.g., a dependent-table error), when the transaction aborts, then no rows for the contact are removed (all-or-nothing).
3. **AC-03**: When a contact is deleted, then a deletion entry is written to the tamper-evident audit log in the same commit (`SEC-8.1`).
4. **AC-04 (negative)**: Given a contact owned by another user, when delete is attempted, then the API returns not-found/forbidden and removes nothing (`SEC-2.2`).
5. **AC-05 (negative)**: Given the audit write fails, when the delete is attempted, then the deletion is not applied (fail closed, `SEC-8.1`).

## Failure Behavior
- **On Invalid Input**: Reject unknown/cross-user contact id with not-found/forbidden; no rows removed.
- **On System Error**: Fail closed — transaction rolls back; nothing is deleted; least-information 500.
- **Alerting**: A partial-delete inconsistency detected by post-delete verification MUST raise an operational alert.

## Test Strategy
- **Unit Tests**: Cascade resolver enumerates all dependent tables for a contact; transaction boundary covers all writes plus the audit entry.
- **Integration Tests**: Delete a contact with reminders, contact events, and outreach history; assert zero residual rows across all tables; inject a mid-cascade failure and assert full rollback.
- **Security Tests**: Cross-user delete denied (TEST-1.3); forced audit-write failure leaves contact intact.
- **Compliance Tests**: Post-deletion query evidence for `FR-1.3`; audit-entry presence for the deletion (`PRIV-1.6`/`SEC-8.1` for contact-level erasure).
- **Coverage Target**: ≥ 80% branch coverage of the deletion/cascade module.

## Dependencies
- **Upstream**: 010 (per-user persistence/transactions), 012 (audit log), 014 (authorization).
- **Downstream**: 048 (full account erasure reuses/extends this cascade across the whole data set).
- **External**: None (DB transaction semantics from the chosen engine — resolved: PostgreSQL, DECISION 069; cascade stays behind the persistence interface and executes as a single atomic transaction).

## Implementation Notes
- **Constraints**: This is **single-contact** deletion, distinct from full **account erasure** (issue 048), which adds provider-token purge, derived-detection purge, backup retention scope, and the surviving proof-of-erasure record (`PRIV-1.16`). Keep the cascade enumeration data-driven so new dependent tables are added in one place.
- **Anti-Patterns**: MUST NOT soft-delete or tombstone contact personal data in place of a hard removal here; MUST NOT delete across multiple transactions (no atomicity gap); MUST NOT skip the audit write to "speed up" the delete.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Atomic multi-table cascade with a fail-closed audit-in-same-commit invariant is exactly where a missed dependent table or a transaction-boundary slip leaks personal data; favor the model with stronger reasoning about transactional consistency and erasure completeness. Mandatory human privacy review before merge.
