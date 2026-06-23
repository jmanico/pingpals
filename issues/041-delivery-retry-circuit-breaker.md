# Requirement: Bounded delivery-path retries, per-channel circuit breaker, bounded DLQ

## Metadata
- **ID**: REQ-DEL-041
- **Title**: Max attempts + backoff/jitter, per-channel breaker, bounded dead-letter queue, bounded dependency calls
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Functional

## Requirement
- **Description**: Delivery-path retries MUST be **bounded** and MUST NOT amplify a provider failure. Each reminder MUST have a **maximum delivery-attempt count**; retries MUST use **exponential backoff with jitter**. A **per-channel circuit breaker** MUST suspend sends to a channel after a configured consecutive-failure threshold and **fail closed** (no further attempts on that channel until reset) rather than retrying continuously. Messages whose attempts are exhausted MUST move to a **dead-letter store of bounded size and retention**; DLQ saturation MUST raise an operational alert and MUST NOT silently drop a reminder. Additionally, calls to critical external dependencies (the managed key store, the datastore, the reminder queue, and delivery providers) MUST be made through **bounded timeouts and a circuit breaker, with bounded (non-infinite) retry**; a transient dependency outage MUST fail closed for any security/privacy decision and MUST NOT degrade into a weaker path. This is delivery-path retry control and is **distinct** from the per-user generation cap (issue 032 / `SEC-6.2`).
- **Rationale**: An unbounded retry against a failing provider amplifies the outage, exhausts worker/queue capacity, and can become a self-inflicted DoS affecting other users (`NFR-1.5`, `NFR-1.6`). Backoff+jitter, a circuit breaker, and a bounded DLQ contain the blast radius; bounded dependency calls keep a single dependency hiccup from cascading. Failing closed on security/privacy decisions during an outage preserves `SEC-2.3`/`SEC-3.1`.
- **Design**: Per `DESIGN.md` §6, a delivery that ultimately fails surfaces a gentle, non-blaming message ("The royal messenger will try again"); the user is never shown an internal error or a duplicate flood.

## Scope
- **Applies To**: API / Backend (delivery worker, dependency clients)
- **Components**: Delivery worker retry/breaker logic; per-channel circuit breakers; dead-letter store; bounded clients for KMS (011), datastore (010), queue, and delivery providers (038/040); alerting hooks; delivery audit (042).
- **Actors**: Internal delivery worker; external delivery providers and infrastructure dependencies.
- **Data Classification**: Restricted (dead-lettered reminder references — minimal, no message content per 042); Internal (breaker/metric state).

## Security Context
- **Defense Layer**: Architecture (resilience / abuse-resistance) + fail-closed dependency handling
- **Threat(s) Addressed**: Retry amplification / self-DoS (CWE-770 uncontrolled resource consumption, CWE-799 improper control of interaction frequency), fail-open degradation of a security decision during outage (CWE-636). STRIDE: Denial of Service.
- **Trust Boundary**: The worker→provider and worker→infrastructure-dependency boundaries; failures there are contained, not allowed to cascade across users.
- **Zero Trust Consideration**: A degraded dependency is never trusted to "probably succeed" — security/privacy decisions fail closed under outage rather than retrying into a weaker path, and capacity is protected by hard bounds.

## Standards Alignment
- **OWASP ASVS**: V11/V14 (business-logic & operational resilience), V7 (error handling)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SC-5 (DoS protection), SI-13 (predictable failure prevention), CP-10 (recovery)
- **NIST SP 800-207**: fail-closed under degraded conditions
- **Regulatory**: n/a directly (supports availability of consented delivery, `FR-6.2`)
- **Other**: `NFR-1.5`, `NFR-1.6`, `SEC-2.3`, distinct from `SEC-6.2` (issue 032)

## Acceptance Criteria
1. **AC-01**: Given a reminder delivery, when an attempt fails, then it is retried with exponential backoff + jitter up to the configured maximum attempt count, after which it moves to the DLQ.
2. **AC-02 (verbatim `NFR-1.5`)**: Given a simulated sustained provider outage, when delivery is attempted, then the breaker trips, producing no unbounded retry or DLQ growth, and does not exhaust worker or queue capacity for other users.
3. **AC-03**: Given a tripped per-channel circuit breaker, when further reminders target that channel, then no attempts are made until the breaker resets (fail closed).
4. **AC-04 (negative)**: Given the DLQ reaches its bounded size, when another reminder is dead-lettered, then an operational alert is raised and no reminder is silently dropped.
5. **AC-05 (negative)**: Given a transient KMS/datastore/queue outage, when a security/privacy decision is required, then the call uses a bounded timeout + breaker + bounded retry and fails closed (no weaker path, no unbounded retry) within the configured timeout (`NFR-1.6`).

## Failure Behavior
- **On Invalid Input**: n/a (operates on already-validated, cleared reminders from 035).
- **On System Error**: Fail closed for security/privacy decisions; for transport failures, bounded retry then DLQ; breaker suspends the channel on the consecutive-failure threshold.
- **Alerting**: Breaker trip, DLQ saturation, and dependency-timeout breaker trips MUST raise operational alerts.

## Test Strategy
- **Unit Tests**: Attempt-count cap; backoff+jitter schedule; breaker open/half-open/close transitions; DLQ bound and saturation alert; dependency client timeout/breaker/bounded-retry.
- **Integration Tests**: Sustained provider outage trips the breaker with no unbounded retry/DLQ growth and no cross-user capacity exhaustion; injected KMS/datastore timeout fails closed within the timeout.
- **Security Tests**: Fault-injection / chaos test confirming no fail-open path and no retry amplification (maps to `NFR-1.5`/`NFR-1.6` resilience verification).
- **Compliance Tests**: Each terminal outcome (delivered/retried/dead-lettered) is recorded via the delivery audit (042).
- **Coverage Target**: ≥ 80% branch coverage of the retry/breaker/DLQ modules.

## Dependencies
- **Upstream**: 010 (datastore client), 011 (KMS client), 012 (audit), 035 (cleared delivery), queue/broker decision issue.
- **Downstream**: 038 (email adapter), 040 (push adapter), 042 (delivery audit records outcomes).
- **External**: Delivery providers; chosen durable queue and dead-letter store (decision issue).

## Implementation Notes
- **Constraints**: All bounds (max attempts, breaker thresholds, DLQ size/retention, timeouts) MUST be configurable and default to conservative values. Queue/DLQ backend is `TO BE DECIDED` — keep behind an interface; DLQ retention is `PRIV-1.9`-bound and carries minimal references only (042). Any in-memory retention of decrypted key material to absorb a KMS hiccup is **out of scope** here and owned by `SEC-3.1` — MUST NOT be introduced under this requirement (`NFR-1.6`).
- **Anti-Patterns**: MUST NOT retry without bound or without jitter; MUST NOT keep hammering a channel past the breaker threshold; MUST NOT silently drop a reminder on DLQ saturation; MUST NOT degrade a security/privacy decision to a weaker path during an outage; MUST NOT conflate this with the generation cap (issue 032).
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Resilience logic with a strict fail-closed-for-security constraint and subtle amplification failure modes; favor careful reasoning about cascading failure and capacity exhaustion. Human review confirms no fail-open path and correct breaker semantics.
