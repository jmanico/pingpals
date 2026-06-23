# Requirement: Per-user resource quotas on contacts, categories, and import batch size

## Metadata
- **ID**: REQ-CON-029
- **Title**: Fail-closed per-user quotas bounding contacts, categories, and single-import batch size
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Medium
- **Classification**: Security

## Requirement
- **Description**: The system MUST enforce per-user resource quotas bounding the number of contacts, the number of categories, and the size of any single import batch, so that scheduler evaluation stays within its defined window (`NFR-1.1`) and no single account can exhaust shared storage or the import worker. Exceeding a quota MUST **fail closed**: the create or import MUST be rejected with a field-level error and MUST NOT be silently truncated or partially written.
- **Rationale**: Per-user quotas bound the scheduler's per-window evaluation cost (`NFR-1.1`) and prevent a single account from exhausting shared storage or the import worker (`SEC-6.3`). Failing closed (reject, no partial write) prevents a half-imported address book or a silently truncated batch that the user believes succeeded.
- **Design**: Per `DESIGN.md` §6, the over-quota message is gentle but unambiguous about the limit and that nothing was written.

## Scope
- **Applies To**: Both
- **Components**: Flask API contact/category create endpoints and import endpoint (030); per-user persistence (010); rate-limit/concurrency framework (013).
- **Actors**: Authenticated user (owner).
- **Data Classification**: Restricted (counts of contacts/categories are tied to the user's personal-data set).

## Security Context
- **Defense Layer**: Architecture + Input Validation (resource bounding, fail-closed quota check)
- **Threat(s) Addressed**: Resource exhaustion / DoS via unbounded contacts/categories/import (CWE-770 allocation without limits), scheduler-window blowup, silent truncation. STRIDE: Denial of Service.
- **Trust Boundary**: Client→API edge; quota enforcement is server-side and pre-write.
- **Zero Trust Consideration**: Every create/import is checked against the user's current count before any write; the request is untrusted and cannot self-assert a higher limit.

## Standards Alignment
- **OWASP ASVS**: V11/V7 (business-logic abuse / anti-automation), V5.1 (bounds)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SC-5 (denial-of-service protection), SC-6 (resource availability)
- **NIST SP 800-207**: indeterminate/over-limit decision resolves to deny
- **Regulatory**: GDPR Art. 5(1)(c) minimization (bounded data set)
- **Other**: `SEC-6.3`, `NFR-1.1`, related `SEC-6.1` (rate/concurrency in 013)

## Acceptance Criteria
1. **AC-01 (verbatim `SEC-6.3`)**: Given a create or import request that would exceed the configured quota, when submitted, then it is rejected with no partial write.
2. **AC-02 (verbatim `SEC-6.3`)**: Given any user, when the scheduler evaluates their contacts, then the per-window evaluation cost remains bounded by the contact quota.
3. **AC-03**: Given an over-quota create (contact or category), when submitted, then a field-level error is returned and no row is written.
4. **AC-04 (negative)**: Given an import batch larger than the single-batch limit, when submitted, then it is rejected and not silently truncated or partially written.
5. **AC-05**: Given quotas configured behind an interface, when the deployment quota values change, then enforcement uses the configured values without code changes to callers.

## Failure Behavior
- **On Invalid Input**: Reject over-quota with HTTP 409/400 and a field-level error; no partial write.
- **On System Error**: Fail closed — if the current count cannot be determined, the create/import is rejected rather than allowed.
- **Alerting**: Repeated over-quota rejection for a user MAY raise an operational signal (possible abuse or misconfiguration).

## Test Strategy
- **Unit Tests**: Quota check at contact/category create; single-import-batch size check; configured-value resolution.
- **Integration Tests**: Create up to and past the contact/category quota; submit an over-size import batch; assert fail-closed and no partial write.
- **Security Tests**: Fuzz import-batch size; confirm scheduler per-window cost stays bounded by the quota (load test).
- **Compliance Tests**: Configuration validation that every quota has a default and is enforced.
- **Coverage Target**: ≥ 80% branch coverage of the quota module.

## Dependencies
- **Upstream**: 010 (persistence/counts), 013 (rate limiting & concurrency), 024 (contact create), 026 (category create).
- **Downstream**: 030 (Google People import streams/paginates against the batch bound), 031 (scheduler relies on bounded counts).
- **External**: None.

## Implementation Notes
- **Constraints**: Quota values are configurable behind an interface with most-restrictive defaults until tuned. The import path (issue 030) MUST stream/paginate against the bound rather than load a provider address book wholesale. Concurrency caps for import/export live in issue 013 (`SEC-6.1`).
- **Anti-Patterns**: MUST NOT silently truncate an over-quota import; MUST NOT partial-write then error; MUST NOT serve an unbounded create path that bypasses the quota.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Bounded counting/threshold logic against existing persistence and rate-limit frameworks; mechanical. Human review confirms fail-closed-no-partial-write.
