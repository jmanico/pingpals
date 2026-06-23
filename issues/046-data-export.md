# Requirement: Machine-readable complete data export (DSR access & portability)

## Metadata
- **ID**: REQ-PRIV-046
- **Title**: Machine-readable, complete, round-trippable data export for the requesting user
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Compliance

## Requirement
- **Description**: The system MUST generate a machine-readable data export (for example, JSON) that includes **all** personal data held for the requesting authenticated user. The export MUST round-trip all contact, category, cadence, consent, and history records — that is, the exported artifact MUST be complete enough that every such record could be reconstructed from it. Export generation is a data-subject-request (DSR) action and MUST therefore be rate-limited (013) and audited (012). Access control of the resulting artifact is handled by issue 047 and is out of scope here.
- **Rationale**: GDPR Article 15 (right of access) and Article 20 (data portability) require the controller to provide the data subject's personal data in a structured, commonly used, machine-readable format. An incomplete export silently breaches both rights, so completeness is the load-bearing property. This is the data-of-record behind `PRIV-1.5`.
- **Design**: Per `DESIGN.md` §6, the export request and its "your export is ready" affordance use the gentle royal voice; the artifact itself is plain structured data with no brand styling. The UI presents export as a DSR action alongside erasure and rectification (issue 050).

## Scope
- **Applies To**: Both
- **Components**: Privacy/DSR subsystem — export generator; reads from per-user-scoped repositories (010); enqueues a bounded export job (013).
- **Actors**: Authenticated user (owner) requesting their own data; no other actor may trigger an export for that user.
- **Data Classification**: Restricted/PII — the export aggregates all contact personal data, consent records, and history for one user.

## Security Context
- **Defense Layer**: Architecture (per-user-scoped read) + Strict API
- **Threat(s) Addressed**: Incomplete-export compliance failure, cross-user data leakage into an export, resource exhaustion via repeated/large exports (CWE-400). STRIDE: Information Disclosure, Denial of Service.
- **Trust Boundary**: API service — export reads only through user-scoped repositories so no other user's data can enter the artifact; the artifact then crosses to the access-controlled download boundary owned by issue 047.
- **Zero Trust Consideration**: Every record read for the export carries the owning user as a non-optional constraint (`SEC-2.2`); the generator trusts no ambient "current user" beyond the per-request authorized principal.

## Standards Alignment
- **OWASP ASVS**: V8.x (data protection), V13.x (API), V5.1 (input validation of the request)
- **OWASP AISVS**: n/a (no AI component)
- **NIST SP 800-53**: AC-3 (access enforcement), AU-2 (auditable events), SC-5 (DoS protection via rate limit)
- **NIST SP 800-207**: per-user-scoped, per-request data access
- **Regulatory**: GDPR Arts. 15 (access), 20 (portability), 12 (modalities)
- **Other**: `PRIV-1.5`, `PRIV-1.3`, `SEC-6.1`, `SEC-8.1`

## Acceptance Criteria
1. **AC-01 (verbatim `PRIV-1.5`)**: Given a user requests an export, when the artifact is generated, then an exported file round-trips all contact, category, cadence, consent, and history records.
2. **AC-02**: Given an export request, when generated, then the artifact is machine-readable (e.g. JSON parses against a published schema) and includes all personal data held for the requesting user and no other user's data.
3. **AC-03**: Given an export request, when it is processed, then a DSR audit event is written (012) and the request is counted against the user's DSR rate limit (013).
4. **AC-04 (negative)**: Given a user exceeds the configured DSR export rate or concurrency limit, when they request another export, then the request returns 429 and enqueues no additional export work (`SEC-6.1`).
5. **AC-05 (negative)**: Given user A requests an export, when the artifact is built, then no record owned by user B appears in it (cross-user isolation, `SEC-2.2`).

## Failure Behavior
- **On Invalid Input**: Reject a malformed export request with HTTP 422; no job enqueued.
- **On System Error**: Fail closed — if any source repository cannot be read completely, abort the export and surface a least-information error rather than emitting a partial/incomplete artifact (an incomplete export is a compliance breach, not a degraded success).
- **Alerting**: Repeated export failures or a spike in export volume per user raises an operational alert (no PII in the alert).

## Test Strategy
- **Unit Tests**: Serialization of each entity type (contact, category, cadence, consent, history); completeness assertion that every held record class is represented.
- **Integration Tests**: Seed a user with records across all classes, export, re-import/parse, assert byte-for-record round-trip; assert a second user's data is absent (maps to TEST-1.4 export completeness).
- **Security Tests**: Cross-user export isolation test; rate-limit/concurrency exhaustion returns 429 with no enqueue.
- **Compliance Tests**: Automated evidence that the export schema covers all §3/§6.4 personal-data fields and that a DSR audit event is present per export.
- **Coverage Target**: ≥ 80% branch coverage of the export module.

## Dependencies
- **Upstream**: 010 (per-user-scoped persistence), 012 (audit log), 013 (rate limiting + concurrency), 045 (consent records — exported), 024 (contact CRUD model).
- **Downstream**: 047 (export-artifact access control — secures the generated artifact), 050 (DSR endpoints invoke export for Art. 15/20).
- **External**: None in MVP (artifact storage backend `TO BE DECIDED`; keep behind an interface, default to encrypted, key-separated storage per `SEC-5.6`).

## Implementation Notes
- **Constraints**: Export runs as a bounded background job with a per-user concurrency cap (`SEC-6.1`); stream/paginate large data sets rather than loading wholesale. Artifact MUST be encrypted at rest (handed to 047 for access control + retention).
- **Anti-Patterns**: MUST NOT emit a partial artifact on error; MUST NOT read across users; MUST NOT expose the artifact via a long-lived or unauthenticated URL (that control lives in 047); MUST NOT include another user's data.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Schema-completeness and serialization work that is broad but well-bounded once the entity set is enumerated; suited to systematic coverage. Mandatory human review to confirm the export schema enumerates every personal-data class in §3/§6.4; coordinate the artifact handoff contract with issue 047.
