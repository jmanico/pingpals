# Requirement: Relationship categories — defaults, custom CRUD, fail-closed delete

## Metadata
- **ID**: REQ-CON-026
- **Title**: Default + custom categories with per-category default cadence and reassignment-on-delete
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Functional

## Requirement
- **Description**: The system MUST ship the default categories **Best Friend, Casual Friend, Family, Professional**, each with a configurable default cadence. The system MUST allow the user to create, rename, and delete custom categories, each with its own default cadence. Deleting a category MUST require reassignment of its contacts to another category and MUST **fail closed** if any contact would be left without a category. A contact MUST belong to **exactly one** category at a time.
- **Rationale**: Categories carry the default cadence that drives the reminder engine (`FR-3.2`). The exactly-one-category and fail-closed-delete invariants prevent a contact from becoming uncategorized — which would leave it without an effective cadence and silently drop it from reminders (`FR-2.3`, `FR-2.4`).
- **Design**: Per `DESIGN.md` §5–§6, the royal/court metaphor frames categories ("your court"); the delete flow prompts for a reassignment target rather than orphaning contacts, with gentle, unambiguous copy.

## Scope
- **Applies To**: Both
- **Components**: Flask API category endpoints; React category management UI; per-user persistence (010); contact model (024).
- **Actors**: Authenticated user (owner).
- **Data Classification**: Restricted (category is contact-associated relationship data; category names are user-supplied).

## Security Context
- **Defense Layer**: Input Validation + Architecture (referential integrity, fail-closed delete)
- **Threat(s) Addressed**: Orphaned/uncategorized contacts (logic flaw leading to dropped reminders), injection via category name (CWE-20), cross-user category access (OWASP API1:2023). STRIDE: Tampering, Denial of Service (silently lost reminders).
- **Trust Boundary**: Client→API edge; referential-integrity and reassignment checks execute server-side.
- **Zero Trust Consideration**: Category names validated against an explicit bounded schema; all category and reassignment operations are user-scoped and per-request authorized (`SEC-2.2`).

## Standards Alignment
- **OWASP ASVS**: V5.1 (input validation), V13/V11 (access control)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SI-10, AC-3
- **NIST SP 800-207**: per-request, user-scoped authorization
- **Regulatory**: GDPR Art. 25 privacy by design (privacy-protective defaults)
- **Other**: `FR-2.1`, `FR-2.2`, `FR-2.3`, `FR-2.4`

## Acceptance Criteria
1. **AC-01**: Given a newly provisioned user, when their account is created, then the four default categories exist, each with a configurable default cadence.
2. **AC-02**: Given an authenticated user, when they create, rename, or delete a custom category with its own default cadence, then the change is applied and scoped to that user.
3. **AC-03 (verbatim `FR-2.3`)**: When a category is deleted, then reassignment of its contacts to another category is required, and the delete fails closed if any contact would be left without a category.
4. **AC-04 (verbatim `FR-2.4`)**: At any time, a contact belongs to exactly one category.
5. **AC-05 (negative)**: Given a category-delete that omits a reassignment target while contacts remain, when submitted, then the delete is rejected (fail closed) and no category or contact is modified.
6. **AC-06 (negative)**: Given a category owned by another user, when accessed/modified, then the API returns not-found/forbidden (`SEC-2.2`).

## Failure Behavior
- **On Invalid Input**: Reject with HTTP 400/409 and a field-level error (e.g., invalid name, missing reassignment target); no partial write.
- **On System Error**: Fail closed — no category or contact mutation persists; category delete that cannot guarantee reassignment aborts.
- **Alerting**: An observed uncategorized contact (invariant violation) MUST raise an operational alert.

## Test Strategy
- **Unit Tests**: Default-category seeding; category name validation/bounds; exactly-one-category invariant; reassignment requirement.
- **Integration Tests**: Delete a category holding contacts with and without a reassignment target; assert fail-closed and no orphaned contacts; default cadence inheritance verified against issue 027.
- **Security Tests**: Cross-user category access denied; bounded category count enforced via issue 029.
- **Compliance Tests**: Schema audit confirms category membership is single-valued and never null for a live contact.
- **Coverage Target**: ≥ 80% branch coverage of the category module.

## Dependencies
- **Upstream**: 009 (validation), 010 (per-user persistence), 014 (authorization), 024 (contact model).
- **Downstream**: 027 (cadence config — category default cadence is inherited), 029 (per-user category quota), 031 (scheduler uses effective cadence).
- **External**: None.

## Implementation Notes
- **Constraints**: Default cadences are configurable but seeded with sane defaults. Category count is bounded by the per-user quota (issue 029). Names bounded and ReDoS-safe per SECURITY §4.
- **Anti-Patterns**: MUST NOT allow a contact to have zero or multiple categories; MUST NOT silently null a contact's category on category delete; MUST NOT allow deletion of a category that would orphan contacts.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Well-bounded CRUD with a clear referential-integrity invariant; mechanical once the fail-closed delete rule is encoded. Human review confirms the exactly-one-category and reassignment invariants.
