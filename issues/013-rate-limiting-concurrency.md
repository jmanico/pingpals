# Requirement: Rate limiting and per-user concurrency caps

## Metadata
- **ID**: REQ-BE-013
- **Title**: Endpoint rate limiting, default baseline per-user limit, and concurrency caps for heavy operations
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Security

## Requirement
- **Description**: The API MUST rate-limit authentication, OAuth-callback, DSR (including data access/export and erasure), contact-import, and reminder-delivery endpoints. In addition, every authenticated endpoint MUST have a baseline per-user request-rate limit applied by default and failing closed — an endpoint with no explicit policy MUST inherit the baseline rather than being unlimited. Operations that consume an external provider quota or are CPU/IO heavy — at minimum contact import (`FR-1.5`) and data export (`PRIV-1.5`) — MUST additionally be bounded by a per-user concurrency cap so a single user cannot exhaust shared provider quota or worker capacity. Exceeding a configured request-rate or concurrency limit MUST return `429` and MUST enqueue no additional work.
- **Rationale**: Anchored in `SEC-6.1` (rate-limit sensitive endpoints + default baseline + concurrency caps) and `SEC-6.3` (per-user resource quotas). Default-deny baseline limiting prevents an unlisted endpoint from being silently unlimited; concurrency caps stop a single user from exhausting Google People quota or export workers and starving others.
- **Design**: No user-facing surface beyond a gentle, non-blaming `429` message (DESIGN §6) that does not leak limits in a way that aids evasion.

## Scope
- **Applies To**: Both (server enforces; the SPA surfaces the throttled state).
- **Components**: Flask API service — a rate-limit/concurrency middleware with a pluggable counter store, per-endpoint policy registry with a default baseline, per-user concurrency gate for heavy ops (import, export).
- **Actors**: Authenticated user (per-user keying); unauthenticated auth/OAuth-callback traffic (limited by a separate key, e.g. source/identifier).
- **Data Classification**: Internal (counters/quotas, no personal data); protects Restricted operations (import, export, DSR) from abuse.

## Security Context
- **Defense Layer**: Architecture + Abuse Prevention (default-deny rate/concurrency control).
- **Threat(s) Addressed**: Brute-force/credential-stuffing on auth (CWE-307), resource-exhaustion DoS (CWE-400), provider-quota exhaustion / noisy-neighbor starvation, DSR/export abuse. STRIDE: Denial of Service, Elevation of Privilege (via flooding).
- **Trust Boundary**: The Flask boundary — limits are enforced server-side per request; an unlisted endpoint still inherits the baseline so the boundary is never implicitly unlimited.
- **Zero Trust Consideration**: No endpoint is trusted to be safe-by-omission; the absence of an explicit policy fails closed to the baseline limit rather than to unlimited access.

## Standards Alignment
- **OWASP ASVS**: V11.1 (business-logic/anti-automation), V13.4 (API rate limiting)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SC-5 (denial-of-service protection), AC-12 (session/rate controls), SI-10 (input handling)
- **NIST SP 800-207**: default-deny posture for unenumerated endpoints
- **Regulatory**: GDPR Art. 32 (resilience/availability of processing)
- **Other**: SECURITY.md §7; `SEC-6.1`, `SEC-6.3`, `FR-1.5`, `PRIV-1.5`

## Acceptance Criteria
1. **AC-01 (verbatim `SEC-6.1`)**: Given the configured request-rate or concurrency limit on each of auth/OAuth-callback/DSR/import/delivery endpoints, when it is exceeded, then the endpoint returns `429` and enqueues no additional work; and an endpoint with no explicit policy is rejected at the baseline limit, not served unbounded.
2. **AC-02**: Given two concurrent contact-import (or export) requests by the same user beyond the per-user concurrency cap, when issued, then the excess is rejected (`429`) without starting additional provider-quota-consuming work.
3. **AC-03 (negative)**: Given a newly added authenticated endpoint with no explicit limit, when hammered, then it is throttled at the baseline (not unlimited) — verified by a test that asserts the baseline applies by default.
4. **AC-04 (negative)**: Given repeated authentication attempts beyond the auth limit, when made, then they are throttled (`429`) and no auth work is performed for the excess (supports brute-force resistance).
5. **AC-05**: Given a `429` is returned, when inspected, then no internal limit configuration is disclosed beyond what is necessary (e.g. a `Retry-After`), and the response is non-blaming (DESIGN §6).

## Failure Behavior
- **On Invalid Input**: Over-limit requests return `429` with `Retry-After`; no work enqueued.
- **On System Error**: Fail closed — if the counter store is unavailable and the limit state is indeterminate, deny (throttle) rather than allow unbounded traffic.
- **Alerting**: Sustained `429` volume or repeated cap-exhaustion by a single user raises an abuse alert.

## Test Strategy
- **Unit Tests**: Limit/counter logic; baseline inheritance for unlisted endpoints; concurrency-gate acquire/release.
- **Integration Tests**: Exceed each listed endpoint's limit → `429`, no enqueue; concurrency cap on import/export; baseline applies to a deliberately-unconfigured endpoint.
- **Security Tests**: Brute-force simulation on auth; quota-exhaustion simulation on import; assert no work performed past the limit.
- **Compliance Tests**: Policy-registry audit evidence that every authenticated endpoint resolves to at least the baseline limit and heavy ops carry a concurrency cap.
- **Coverage Target**: ≥ 80% branch coverage of the rate-limit/concurrency middleware.

## Dependencies
- **Upstream**: 007 (Flask skeleton), 014 (authz PDP — per-user keying needs the authenticated principal).
- **Downstream**: OAuth/auth issues, contact-import (`FR-1.5`), data-export (`PRIV-1.5`), erasure/DSR issues, Delivery worker (`SEC-6.2` scheduler cap is a distinct sibling control), 016 (internal message authn — delivery side).
- **External**: Shared counter store for distributed limiting (engine `TO BE DECIDED`, DECISION 071 reminder-queue/store family) — behind an interface defaulting to fail-closed throttling when unavailable.

## Implementation Notes
- **Constraints**: Counter store must support per-user keys across horizontally-scaled instances (NFR-1.1) — keep behind an interface while the store is `TO BE DECIDED`. The scheduler's per-user reminder generation cap (`SEC-6.2`) and per-user resource quotas (`SEC-6.3` contact/category caps) are related but distinct issues; this one covers endpoint rate-limiting + concurrency caps.
- **Anti-Patterns**: MUST NOT leave any authenticated endpoint unlimited by omission; MUST NOT fail open when the counter store is unavailable; MUST NOT perform/enqueue work for over-limit requests before rejecting; MUST NOT leak full limit configuration in error responses.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** This is a well-understood middleware pattern with clear, enumerable policies; a capable general model implements it efficiently against the explicit endpoint list. Mandatory human review confirms the default-baseline-applies-everywhere invariant and the fail-closed counter-store behavior before merge.
