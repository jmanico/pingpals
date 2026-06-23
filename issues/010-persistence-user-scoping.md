# Requirement: Per-user-scoped persistence layer and core data model

## Metadata
- **ID**: REQ-BE-010
- **Title**: Repository layer with non-optional owning-user scoping and core entity schema
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Critical
- **Classification**: Security

## Requirement
- **Description**: The backend MUST provide a persistence/repository layer in which every query carries the owning user as a NON-OPTIONAL constraint, such that no code path can read or write another user's data. The layer MUST realize the core entities — `User`, `Contact`, `Category`, `Cadence` (interval days + optional preferred day/send window), `Reminder`, `ConsentRecord`, `ContactEvent` (last-contact log), `OutreachAction`, `ProviderToken` (encrypted at rest), and `AuditLogEntry` — with migrations, applying the §3 data classification to each field. The owning-user constraint MUST be structurally enforced (it MUST NOT be possible to construct a fetch/mutation for a Restricted entity without supplying the owning user), and the concrete database engine (DECISION 069 (resolved: PostgreSQL)) MUST remain behind a repository interface, defaulting to the most-restrictive behavior.
- **Rationale**: This is the structural foundation for `SEC-2.2` (all data access user-scoped, no cross-user read/write) and ARCH Dependency Rule 4 (every repository/query carries the owning user as a non-optional constraint). Making the scope non-optional at the repository boundary prevents Broken Object Level Authorization (BOLA) at its root rather than relying on each endpoint to remember to filter.
- **Design**: Entities back the DESIGN.md surfaces (reminder card, contact/category views) but this issue is data-only; no UI. Minimization rules (§3, §6.4, `PRIV-1.7`) bound which fields may exist.

## Scope
- **Applies To**: API
- **Components**: Flask API service — repository/data-access layer, entity models, migration set, repository interface abstracting the DB engine.
- **Actors**: Authenticated user (sole controller of their own data set); the Scheduler/Delivery worker access via the same scoped repositories (their owning-user assertion is authorized per issue 016).
- **Data Classification**: Restricted (`Contact`, `Category`, `Cadence`, `Reminder`, `ConsentRecord`, `ContactEvent`, `OutreachAction`, `ProviderToken`, `AuditLogEntry`); Confidential (`User` credentials/session linkage); per §3.

## Security Context
- **Defense Layer**: Architecture + Authorization (structural tenant isolation at the data layer).
- **Threat(s) Addressed**: Cross-tenant data access / BOLA (CWE-639, OWASP API1:2023), missing owner filter (CWE-285 improper authorization), mass-assignment of owner field (CWE-915 — mitigated jointly with issue 009). STRIDE: Information Disclosure, Tampering, Elevation of Privilege.
- **Trust Boundary**: Inside the Flask boundary — the repository layer is the chokepoint where every data access is bound to exactly one owning user; the React client makes no scoping decision (ARCH Rule 1).
- **Zero Trust Consideration**: No query is trusted to be correctly scoped by its caller; the owning user is a required parameter, so a caller that omits it cannot compile/execute a Restricted read — scope is enforced structurally, not by convention.

## Standards Alignment
- **OWASP ASVS**: V4.1 (access control design), V4.2 (object-level authorization), V8.1 (data protection)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: AC-3 (access enforcement), AC-4 (information flow), SC-4 (information in shared resources)
- **NIST SP 800-207**: per-resource access scoped to the authenticated subject; no implicit trust
- **Regulatory**: GDPR Art. 5(1)(f) integrity/confidentiality, Art. 25 (data protection by design)
- **Other**: SECURITY.md §3; ARCH Dependency Rule 4; `SEC-2.2`, §3 data classification, `PRIV-1.7`

## Acceptance Criteria
1. **AC-01**: Given an authenticated user, when they read or write any owned entity, then the repository scopes the operation to that user's id supplied as a required parameter.
2. **AC-02 (negative, supports verbatim `SEC-2.2`)**: Given user A's session, when any data endpoint backed by these repositories attempts to access user B's object, then the result is not-found or forbidden — automated tests assert this for every data entity.
3. **AC-03 (negative)**: Given the repository API, when a developer attempts to construct a fetch/mutation for a Restricted entity without an owning-user argument, then it does not compile / raises (the owner is non-optional, not a defaultable filter).
4. **AC-04**: Given the entity set, when migrations run, then `User`, `Contact`, `Category`, `Cadence`, `Reminder`, `ConsentRecord`, `ContactEvent`, `OutreachAction`, `ProviderToken`, and `AuditLogEntry` exist with §3-classified fields and owner foreign keys on every owned entity.
5. **AC-05 (negative)**: Given a request that attempts to set/override the owner field on create (mass-assignment), when persisted, then the owner is taken from the authenticated session, not the request body (enforced with issue 009).
6. **AC-06**: Given the engine is PostgreSQL (DECISION 069, resolved), when the layer is built, then all access goes through the repository interface and no query bypasses the owning-user constraint regardless of the underlying engine.

## Failure Behavior
- **On Invalid Input**: A cross-user object reference resolves to not-found/forbidden; no row from another user is returned.
- **On System Error**: Fail closed — an indeterminate scoping state denies access rather than returning unscoped data (`SEC-2.3`).
- **Alerting**: Repeated cross-user access attempts (forbidden/not-found on others' ids) MAY raise a security alert.

## Test Strategy
- **Unit Tests**: Repository methods reject/omit the owner argument at the type/API level; owner is sourced from session not body.
- **Integration Tests**: Two-user fixture; for every entity, assert user A cannot read/update/delete user B's rows (not-found/forbidden) — the canonical cross-user isolation suite (maps to `TEST-1.3` cross-user authorization isolation).
- **Security Tests**: BOLA fuzzing iterating object ids across users; SAST/lint rule flagging any query construction lacking the owner constraint.
- **Compliance Tests**: Schema audit evidence that only §3/§6.4-approved fields exist (supports `PRIV-1.7`); migration review.
- **Coverage Target**: ≥ 80% branch coverage of the repository layer.

## Dependencies
- **Upstream**: 007 (Flask skeleton), 009 (validation — only validated data is persisted), 069 (DECISION: database engine — resolved: PostgreSQL).
- **Downstream**: 011 (KMS encryption-at-rest for `ProviderToken` and other Restricted fields), 012 (audit log `AuditLogEntry`), 014 (authz PDP rides on user-scoped repositories), contact/category/cadence/reminder FR issues, Privacy/DSR erasure-cascade issues (`PRIV-1.6`).
- **External**: Database engine (DECISION 069, resolved: PostgreSQL), accessed behind the repository interface defaulting to deny on indeterminate scope.

## Implementation Notes
- **Constraints**: Engine resolved to PostgreSQL (DECISION 069), still accessed engine-agnostically via the repository interface. Encryption of `ProviderToken` and other Restricted-at-rest fields is delegated to issue 011's KMS interface — store ciphertext + key reference, never plaintext. Audit-log structural tamper-evidence is owned by issue 012; this layer provides the table and the owner/identity columns.
- **Anti-Patterns**: MUST NOT expose an unscoped/global query helper; MUST NOT make the owner an optional/defaultable filter; MUST NOT accept the owner from request input (take it from the authenticated session); MUST NOT store personal-data fields outside the §3/§6.4 approved set; MUST NOT leak whether an object exists across users (return not-found for unauthorized objects).
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Structural tenant isolation is the single most consequential authorization control; a defaultable or omittable owner constraint is a silent cross-tenant breach. Favor the model with stronger reasoning about API-shape invariants that make insecure usage uncompilable. Mandatory human security review of the repository interface and the cross-user isolation test suite before merge.
