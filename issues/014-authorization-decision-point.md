# Requirement: Central per-request authorization decision point (PDP)

## Metadata
- **ID**: REQ-BE-014
- **Title**: Per-request, object- and function-level authorization with fail-closed deny
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Critical
- **Classification**: Security

## Requirement
- **Description**: The API MUST authorize every request per-request against the authenticated user through a central policy decision point, with no trust derived from prior authentication or network position. Authorization MUST be enforced at both the object level (the subject owns/may access the specific object — no BOLA) and the function level (the subject may invoke the operation — no BFLA) on every endpoint. Cross-user object access MUST be answered with not-found or forbidden. An indeterminate or errored policy decision MUST deny (fail closed). The React client MUST NOT make any authorization or data-scoping decision; it presents what the API returns, and all security invariants are enforced server-side.
- **Rationale**: Anchored in `SEC-2.1` (authorize per-request), `SEC-2.2` (user-scoped, no cross-user access), `SEC-2.3` (fail closed), SECURITY.md §3, and ARCH Dependency Rules 1 & 3. A central PDP makes object/function authorization uniform and auditable rather than scattered and forgettable; pairing it with the non-optional repository scope (issue 010) gives defense in depth against BOLA/BFLA — the top OWASP API risks.
- **Design**: No user-facing surface; the SPA renders only authorized data and never gates on client-side checks.

## Scope
- **Applies To**: Both (server enforces; client merely reflects).
- **Components**: Flask API service — central authorization middleware/PDP, per-endpoint object- and function-level policy declarations, deny-by-default resolver. Consumed by every endpoint and (via issue 016's authorization hook) by internal workers.
- **Actors**: Authenticated user (subject of every decision); the PDP itself; internal workers authorize their work items against the asserted owning user.
- **Data Classification**: Restricted (decisions guard access to all owned personal data); Internal (policy declarations).

## Security Context
- **Defense Layer**: Authorization (per-request, fail-closed access control).
- **Threat(s) Addressed**: Broken Object Level Authorization / BOLA (CWE-639, OWASP API1:2023), Broken Function Level Authorization / BFLA (OWASP API5:2023, CWE-285), privilege escalation via missing checks, fail-open on policy error (CWE-636). STRIDE: Elevation of Privilege, Information Disclosure, Tampering.
- **Trust Boundary**: The Flask boundary — every request crosses the PDP before any handler logic; internal east-west calls reuse the same per-item authorization (issue 016).
- **Zero Trust Consideration**: No request is trusted on the basis of a prior successful login or network location; each is authorized afresh against the authenticated subject, and any indeterminate/errored decision denies.

## Standards Alignment
- **OWASP ASVS**: V4.1 (access control design), V4.2 (operation-level authorization), V4.3 (other access control)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: AC-3 (access enforcement), AC-6 (least privilege), AC-24 (access control decisions)
- **NIST SP 800-207**: per-request authorization; no implicit trust from prior state or network position
- **Regulatory**: GDPR Art. 5(1)(f) integrity/confidentiality, Art. 32 (access control)
- **Other**: SECURITY.md §3; ARCH Dependency Rules 1 & 3; `SEC-2.1`, `SEC-2.2`, `SEC-2.3`; OWASP API Security Top 10

## Acceptance Criteria
1. **AC-01**: Given an authenticated request, when it reaches any endpoint, then the PDP evaluates both object-level (owns the target) and function-level (may invoke the operation) authorization before the handler runs.
2. **AC-02 (negative, supports verbatim `SEC-2.2`)**: Given user A's session, when A requests user B's object on any endpoint, then the PDP returns not-found or forbidden — automated tests assert this for every data endpoint.
3. **AC-03 (negative, `SEC-2.3`)**: Given a policy evaluation that errors or is indeterminate, when the decision is resolved, then the result is deny (fail closed), and the denial is recorded in the audit log (`SEC-8.1`).
4. **AC-04 (negative)**: Given a user lacking the role/capability for a function, when they invoke it, then the PDP denies (no BFLA), independent of whether they own any referenced object.
5. **AC-05 (negative)**: Given the React client suppresses or relaxes a UI gate, when a request is sent anyway, then the server PDP still enforces the decision (client makes no authorization decision, ARCH Rule 1).
6. **AC-06 (negative)**: Given a valid session but no network/positional trust, when a request arrives from an internal-looking source, then authorization is still evaluated per-request (no trust by position, `SEC-2.1`).

## Failure Behavior
- **On Invalid Input**: Unauthorized object access → not-found/forbidden; unauthorized function → forbidden; both audited.
- **On System Error**: Fail closed — an errored/indeterminate decision denies (`SEC-2.3`).
- **Alerting**: A spike in authorization denials (especially cross-user object probes) raises a security alert.

## Test Strategy
- **Unit Tests**: PDP resolver deny-by-default; object- and function-level checks independently; error/indeterminate → deny.
- **Integration Tests**: Cross-user object access across every data endpoint returns not-found/forbidden (the canonical `TEST-1.3` isolation suite, jointly with issue 010); function-level access matrix per role/capability.
- **Security Tests**: BOLA/BFLA fuzzing iterating ids and operations across users; assert no fail-open path under injected policy errors.
- **Compliance Tests**: Evidence that every endpoint is registered with an explicit object+function policy (no unguarded endpoint); audit entries for denials.
- **Coverage Target**: ≥ 80% branch coverage of the PDP and policy resolver.

## Dependencies
- **Upstream**: 007 (Flask skeleton), 010 (user-scoped repositories the PDP relies on), 012 (audit log for denials), auth/session issues (provide the authenticated principal).
- **Downstream**: Every API endpoint, 015 (CSRF is a complementary request-authenticity control), 016 (internal workers reuse per-item authorization), 013 (rate limiting keys on the authenticated principal).
- **External**: None (policy is in-process; no external PDP service introduced without `SEC-9.x` vetting).

## Implementation Notes
- **Constraints**: The PDP must be impossible to bypass — wire it as mandatory middleware so an endpoint cannot opt out silently; every endpoint must declare an explicit object+function policy. Pair with issue 010 so a passed authorization still cannot reach an unscoped query.
- **Anti-Patterns**: MUST NOT default to allow when a policy is missing/errored; MUST NOT rely on client-side gating; MUST NOT distinguish "exists but unauthorized" from "not found" in a way that enables enumeration (return not-found for unauthorized objects); MUST NOT grant function access purely from object ownership (object and function are separate checks).
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Authorization is the highest-consequence control surface, where a single fail-open branch or a conflated object/function check is directly exploitable across tenants. Favor the model with stronger reasoning about default-deny invariants and exhaustive endpoint coverage. Mandatory human security review of the resolver and the per-endpoint policy registry before merge.
