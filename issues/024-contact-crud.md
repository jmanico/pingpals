# Requirement: Contact create / edit / delete with reject-over-sanitize validation

## Metadata
- **ID**: REQ-CON-024
- **Title**: Contact CRUD with explicit-schema validation, no coercion, no mass-assignment
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Functional

## Requirement
- **Description**: The system MUST allow an authenticated user to create a contact with at minimum a display name (all other fields optional), edit any contact they own, and delete any contact they own. Every contact field MUST be validated against an explicit schema and invalid input MUST be **rejected** with a field-level error rather than coerced, with no partial write. Contact writes MUST NOT mass-assign: only the approved contact fields are accepted, unknown fields are rejected, and consent fields MUST NOT be settable through any contact write (consent is governed by the immutable consent store, `PRIV-1.15`).
- **Rationale**: Contacts are personal data of third-party data subjects (`§3`, Restricted). Reject-over-sanitize (`FR-1.4`, SECURITY §4) prevents malformed or attacker-shaped data from entering the store; the no-mass-assignment rule prevents privilege/consent escalation through an ordinary write path.
- **Design**: Per `DESIGN.md` §6, validation errors stay gentle and non-blaming but MUST NOT soften a validation failure into ambiguity; the form surfaces a field-level error and performs no write.

## Scope
- **Applies To**: Both
- **Components**: Flask API contact endpoints; React 19 contact form/views; shared validation framework (009); per-user persistence (010).
- **Actors**: Authenticated user (owner). Contact-supplied/contact-derived strings are untrusted input.
- **Data Classification**: Restricted (contact name, phone, email, notes, category).

## Security Context
- **Defense Layer**: Input Validation (explicit schema, reject on failure)
- **Threat(s) Addressed**: Injection/malformed-data via coercion (CWE-20), mass-assignment / privilege escalation (CWE-915, OWASP API3:2023), broken object-level authorization (OWASP API1:2023). STRIDE: Tampering, Elevation of Privilege.
- **Trust Boundary**: Client→API edge — the API is the single trust boundary; the React client makes no authorization or data-scoping decision (ARCH Rule 1).
- **Zero Trust Consideration**: Every field is validated server-side against an explicit schema regardless of client-side validation; every write is authorized per-request and user-scoped (`SEC-2.1`, `SEC-2.2`).

## Standards Alignment
- **OWASP ASVS**: V5.1 (input validation), V13/V11 (object-level access control)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SI-10 (input validation), AC-3 (access enforcement)
- **NIST SP 800-207**: per-request authorization inside the boundary
- **Regulatory**: GDPR Art. 5(1)(c) data minimization, Art. 25 privacy by design
- **Other**: `FR-1.1`, `FR-1.2`, `FR-1.4`, `PRIV-1.15`, `SEC-4.1`, OWASP API Security Top 10

## Acceptance Criteria
1. **AC-01**: Given an authenticated user, when they create a contact supplying only a display name, then the contact is created with all other fields null/absent and is scoped to that user.
2. **AC-02**: Given an authenticated user, when they edit or delete a contact they own, then the change is applied; deletion is delegated to the cascade in issue 025.
3. **AC-03 (verbatim `FR-1.4`)**: Given an invalid phone or email, when the contact is submitted, then it is rejected with a field-level error and no partial write occurs.
4. **AC-04 (negative)**: Given a write containing an unknown field or a consent field, when submitted, then the request is rejected (no mass-assignment) and no consent state changes (`PRIV-1.15`).
5. **AC-05 (negative)**: Given a contact owned by another user, when the user attempts to edit or delete it, then the API returns not-found/forbidden and performs no write (`SEC-2.2`).

## Failure Behavior
- **On Invalid Input**: Reject with HTTP 400 and a field-level error; log via audit subsystem (012) with correlation id; disclose no internal state; perform no partial write.
- **On System Error**: Fail closed — no write is persisted; return a least-information 500.
- **Alerting**: Elevated validation-rejection or cross-user-access-denied rate MAY raise an operational alert.

## Test Strategy
- **Unit Tests**: Schema validation per field (display name required; phone/email/notes/category optional and bounded), unknown-field rejection, consent-field rejection.
- **Integration Tests**: Create/edit/delete round-trip against per-user store; assert no partial write on rejection.
- **Security Tests**: Cross-user edit/delete returns not-found/forbidden (maps to TEST-1.3 cross-user isolation); mass-assignment attempt rejected.
- **Compliance Tests**: Schema audit confirms only approved fields are accepted (`PRIV-1.7`).
- **Coverage Target**: ≥ 80% branch coverage of the contact module.

## Dependencies
- **Upstream**: 009 (validation framework), 010 (per-user persistence/scoping), 012 (audit log), 014 (authorization decision point).
- **Downstream**: 025 (deletion cascade), 026 (category — contact belongs to exactly one category), 027 (cadence config), 030 (Google People import reuses the schema).
- **External**: None.

## Implementation Notes
- **Constraints**: All fields bounded (max length / cardinality) per SECURITY §4; phone/email validated by linear-time, ReDoS-safe validators. Quotas on contact count are enforced by issue 029.
- **Anti-Patterns**: MUST NOT coerce/sanitize invalid input into a "best guess"; MUST NOT accept unknown fields or set consent through this path; MUST NOT use client-side validation as sole enforcement.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Straightforward CRUD against an established validation/persistence framework; mechanical and well-bounded. Human review confirms reject-over-sanitize and no-mass-assignment are enforced server-side.
