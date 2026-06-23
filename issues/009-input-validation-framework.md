# Requirement: Server-side input validation framework (schema, bounds, body-size, ReDoS-safe)

## Metadata
- **ID**: REQ-BE-009
- **Title**: Reject-over-sanitize input validation framework for every inbound edge
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Critical
- **Classification**: Security

## Requirement
- **Description**: The API MUST validate every inbound edge — user input, provider responses, and webhook payloads — against an explicit schema and MUST reject on failure rather than coerce or sanitize (reject over sanitize); provider responses MUST be treated as untrusted until validated. Schemas MUST reject unknown fields and MUST NOT mass-assign. Every schema field MUST declare explicit upper bounds (maximum string length, array/collection cardinality, numeric range); unbounded/open-ended fields MUST NOT be accepted. The API MUST enforce a hard maximum request-body size at the HTTP boundary, rejecting an oversized request with `413` before deserialization and without buffering the full payload into application memory. Validation MUST be safe against catastrophic backtracking (ReDoS): apply a length cap before matching, use anchored/bounded or non-backtracking patterns, never compile untrusted input into a regex, and enforce a per-request validation time/size budget that rejects under resource pressure. All bounds fail closed: an over-limit field or body is rejected, never truncated or coerced.
- **Rationale**: This is the single backend chokepoint behind `FR-1.4` (reject over sanitize) and `SEC-4.1` (validate all external input). Mass-assignment and unbounded fields are direct paths to privilege escalation and DoS; an unbounded body or a backtracking regex is a denial-of-service primitive (the abuse-prevention intent of `SEC-6.x`). Trusting provider responses without validation is an injection vector (ARCH Dependency Rule 2).
- **Design**: No user-facing surface, but field-level rejection messages must stay gentle and non-blaming (DESIGN §6) without softening a validation failure into ambiguity (`FR-1.4`) or leaking internals.

## Scope
- **Applies To**: Both (server is authoritative; the SPA mirrors with Zod per `FE-1.2`, issue downstream).
- **Components**: Flask API service — a validation layer (schema definitions, request-body-size guard at the WSGI/boundary level, a vetted schema/validation library, safe-pattern helpers) consumed by every endpoint and every provider/webhook ingestion path.
- **Actors**: Authenticated user; integration providers (responses untrusted); webhook senders (untrusted until signature + schema pass).
- **Data Classification**: Restricted (contact personal data fields), Confidential (auth payloads) — all validated here before any write.

## Security Context
- **Defense Layer**: Input Validation (allowlist schema, reject over sanitize).
- **Threat(s) Addressed**: Mass assignment / over-posting (CWE-915), injection via unvalidated input/provider response (CWE-20, OWASP A03:2021), ReDoS (CWE-1333), memory-exhaustion DoS via oversized body (CWE-400), type confusion. STRIDE: Tampering, Denial of Service, Elevation of Privilege.
- **Trust Boundary**: Every inbound edge of the Flask boundary — user requests, provider API responses, and inbound webhooks each pass schema validation before any business logic.
- **Zero Trust Consideration**: Provider responses are explicitly untrusted and validated identically to user input; no input is processed on the basis of its source. Bounds are enforced before deserialization and before matching, so adversarial input cannot consume resources to bypass the check.

## Standards Alignment
- **OWASP ASVS**: V5.1 (input validation), V13.1 (API request integrity), V5.2 (sanitization/no mass-assign)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SI-10 (information input validation), SC-5 (denial-of-service protection)
- **NIST SP 800-207**: untrusted input at and inside the boundary
- **Regulatory**: GDPR Art. 5(1)(c) data minimization (reject fields outside the approved set)
- **Other**: SECURITY.md §4; OWASP API Security Top 10, REST Security Cheat Sheet; `FR-1.4`, `SEC-4.1`, ARCH Dependency Rule 2

## Acceptance Criteria
1. **AC-01**: Given a valid request conforming exactly to an endpoint's schema, when submitted, then it is accepted and processed.
2. **AC-02 (negative, verbatim `SEC-4.1` §4 bounds clause)**: Given a request whose body exceeds the size cap, when received, then it is rejected (`413`) before any business logic runs, and a field exceeding its declared maximum length or cardinality is rejected with a field-level error and no partial write.
3. **AC-03 (negative, verbatim `SEC-4.1` §4 ReDoS clause)**: Given a fuzz/complexity test against each validator (phone, email, outreach-URL allowlist, category name), when run with adversarial input, then no validator exceeds a bounded CPU time.
4. **AC-04 (negative)**: Given a request containing unknown/extra fields (including a privileged field like an owner id or consent field), when validated, then the unknown fields are rejected (no mass-assignment) rather than silently accepted.
5. **AC-05 (negative)**: Given a malformed or out-of-schema provider/webhook response, when ingested, then it is rejected and not trusted (`SEC-4.1`, ARCH Rule 2).
6. **AC-06 (negative)**: Given an over-limit field, when validated, then it is rejected — never truncated or coerced to fit (reject over sanitize, `FR-1.4`).

## Failure Behavior
- **On Invalid Input**: Reject with `400` (field-level error) or `413` (oversized body); log a correlation id with no payload contents/PII; no partial write occurs.
- **On System Error**: Fail closed — if validation cannot complete (including hitting the per-request validation budget), the input is rejected, not processed.
- **Alerting**: A sustained spike in `413`/validation-budget rejections MAY raise an abuse/DoS alert.

## Test Strategy
- **Unit Tests**: Per-schema accept/reject tables; unknown-field rejection; bound enforcement (length, cardinality, numeric range); reject-not-truncate behavior.
- **Integration Tests**: Oversized-body rejection before deserialization across representative endpoints; provider-response and webhook-payload validation paths.
- **Security Tests**: ReDoS fuzz/complexity corpus against each validator (maps to the §4 ReDoS verification); mass-assignment probe attempting to set owner/consent fields; SAST rule banning compilation of untrusted input into regex.
- **Compliance Tests**: Schema audit evidence that only approved fields are accepted (supports `PRIV-1.7` minimization).
- **Coverage Target**: ≥ 80% branch coverage of the validation layer.

## Dependencies
- **Upstream**: 007 (Flask skeleton), 069 (DECISION: database — informs schema realization; validation is engine-independent).
- **Downstream**: 010 (persistence — only validated data is written), 014 (authz PDP — operates on validated requests), 015 (CSRF), 055 (URL allowlist is a specialized validator that reuses these length-cap/ReDoS rules), contact/category/cadence FR issues.
- **External**: A vetted schema/validation library (subject to `SEC-9.x` minimization/vetting before introduction).

## Implementation Notes
- **Constraints**: Body-size guard must operate at the WSGI/boundary level (stream/short-circuit before full buffering). Length caps applied before any regex. Keep validators pure and time-bounded.
- **Anti-Patterns**: MUST NOT sanitize/coerce to "fix" invalid input — reject it; MUST NOT mass-assign or accept unknown fields; MUST NOT trust provider responses without validation; MUST NOT compile untrusted input into a regex or use unbounded/greedy backtracking patterns; MUST NOT buffer an oversized body into memory before rejecting it; MUST NOT rely on client-side (Zod) validation as the sole enforcement — server is authoritative.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** The ReDoS-safety, mass-assignment, and reject-over-sanitize invariants are subtle and security-critical; a missed greedy quantifier or accepted unknown field is directly exploitable. Favor stronger adversarial reasoning on parser/regex edge cases. Mandatory human security review of all field bounds and patterns before merge.
