# Requirement: DECISION — durable queue / broker for reminder enqueue, retry, dead-letter

## Metadata
- **ID**: REQ-DEC-070
- **Title**: Decide and document the durable queue/broker between Scheduler and Delivery worker
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Operational
- **Decision**: **STILL DEFERRED — `TO BE DECIDED`.** Remains open behind the queue interface, defaulting to the most-restrictive (durable, authenticated, bounded) behavior; the cloud/region is intentionally deferred cloud-agnostic (decision 073).

## Requirement
- **Description**: The team MUST decide and document the durable queue/broker used to enqueue reminders from the Scheduler to the Delivery worker, including its retry and dead-letter (DLQ) support (`ARCHITECTURE.md` `TO BE DECIDED`). The decision MUST be recorded with rationale against the criteria below, satisfy every listed constraint, and be signed off by a human before the enqueue/worker code (031/041/016) is built. This issue produces NO implementation code and MUST NOT silently resolve the choice (`CLAUDE.md`).
- **Rationale**: The Scheduler→Delivery path requires durability, idempotency, bounded retry, and a dead-letter store (`FR-5.2`, `NFR-1.2`, `NFR-1.5`). The `ARCHITECTURE.md` `[ASSUMPTION]` notes a durable queue is needed but the concrete broker is `TO BE DECIDED`. Internal messages also cross a trust boundary and must be authenticable (`SEC-2.2` inside the boundary, issue 016).
- **Design**: Not a UI feature; `DESIGN.md` does not apply beyond preserving the minimal-payload rule (`FR-5.4`) for any message body.

## Scope
- **Applies To**: API/backend (internal east-west infrastructure)
- **Components**: Scheduler (031), delivery retry/circuit-breaker (041), internal message authentication (016), delivery worker (035), delivery audit events (042).
- **Actors**: Scheduler (producer), Delivery worker (consumer); human approver for sign-off.
- **Data Classification**: Restricted (messages reference reminders/owning user; bodies kept minimal per `FR-5.4`).

## Security Context
- **Defense Layer**: Architecture (internal messaging infrastructure).
- **Threat(s) Addressed**: Lost/duplicate reminders from a non-durable or non-idempotent queue (DoS/notification flooding), forged or replayed internal messages (CWE-345), unbounded retry amplifying a provider outage (`NFR-1.5`), DLQ saturation silently dropping reminders. STRIDE: Spoofing, Tampering, Denial of Service, Repudiation.
- **Trust Boundary**: Internal service-to-service boundary; Zero Trust applies INSIDE the boundary — the worker MUST NOT trust a work item on network position alone (SECURITY.md §3, `SEC-2.1`).
- **Zero Trust Consideration**: Every work item MUST be authenticated to its producer and authorized against its asserted owning user before action (issue 016); the broker choice MUST support a signed/MAC'd or mTLS envelope and per-message authorization.

## Standards Alignment
- **OWASP ASVS**: V1.x (architecture), V13/V14 (API/config)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SC-8 (transmission integrity), SC-5 (DoS protection), SI-4 (monitoring/DLQ alerting)
- **NIST SP 800-207**: authenticate internal traffic; deny-by-default for work items
- **Regulatory**: GDPR Art. 32 (security of processing) — internal message integrity for PII-referencing work
- **Other**: `FR-5.2`, `NFR-1.2`, `NFR-1.5`, `SEC-2.1`, `SEC-2.2`, `SEC-6.2`, ARCH Dependency Rule 8

## Evaluation Criteria (constraints any choice MUST satisfy)
1. **Durability** — messages survive broker/worker restarts so a due reminder is not lost (`NFR-1.2`).
2. **Idempotency-key support** — supports deduplication so one due event yields no duplicate reminder, even on redelivery (`FR-5.2`, ARCH Rule 8).
3. **Dead-letter queue** — bounded-size DLQ with retention; saturation raises an operational alert and never silently drops a reminder (`NFR-1.5`).
4. **Bounded retry with backoff** — supports a max attempt count and exponential backoff with jitter, distinct from the per-user generation cap (`NFR-1.5`, `SEC-6.2`).
5. **Internal message authentication** — supports a signed/MAC'd envelope or mTLS so a forged/replayed message is rejected (issue 016, `SEC-2.1`).
6. **Per-user fairness / isolation** — a single user's backlog cannot starve other users' deliveries (`NFR-1.5`, `NFR-1.1`).
7. **Cloud-portable** — no hard dependency on a single cloud's proprietary broker (ARCH "many clouds"); runnable in the Docker deployment.

## Candidate Options (evaluate, do NOT pick here)
- A self-hostable broker with native DLQ and delayed/retry support (e.g. a message broker with dead-letter exchanges).
- A durable log/stream platform with consumer offsets (evaluate against per-message DLQ and delayed-retry ergonomics).
- A database-backed durable job queue (evaluate against scale and fairness constraints).
- A managed cloud queue (evaluate against the cloud-portability constraint and decision 073's region choice).

> Each option MUST be scored against all seven criteria with rationale. This issue does not select one.

## Acceptance Criteria
1. **AC-01**: Given the candidate options, when evaluated, then each is scored against all seven criteria with documented rationale.
2. **AC-02**: Given the evaluation, when a choice is recommended, then it is recorded in `ARCHITECTURE.md` (replacing the relevant `TO BE DECIDED`/`[ASSUMPTION]`) with rationale and explicit human sign-off.
3. **AC-03 (negative)**: Given any candidate lacking durability, DLQ, idempotency-key support, or an authenticable envelope, when evaluated, then it is rejected and the reason recorded.
4. **AC-04 (negative — no silent resolution)**: Given this issue, when worked, then no enqueue/worker code (031/041/016) is built and no broker is committed before human sign-off; until then the path stays behind a queue interface defaulting to the most-restrictive (durable, authenticated, bounded) behavior.

## Failure Behavior
- **On Invalid Input**: n/a (decision artifact).
- **On System Error**: Until resolved, dependents (031, 041, 016, 042) stay blocked or behind the queue interface; no broker is assumed.
- **Alerting**: Flag downstream issues as decision-blocked on the board while this is open.

## Test Strategy
- **Unit Tests**: n/a (no code). Provide a decision matrix artifact.
- **Integration Tests**: Optional spike validating durability, idempotent redelivery, DLQ routing, and envelope authentication on the front-runner; results feed the decision only.
- **Security Tests**: Threat-review the front-runner against forged/replayed-message and DLQ-saturation scenarios.
- **Compliance Tests**: Confirm message bodies can stay minimal (`FR-5.4`) and PII-free where the channel is untrusted (`FR-5.6`).
- **Coverage Target**: n/a (decision issue).

## Dependencies
- **Upstream**: 016 (internal message authentication design constraints), decision 073 (hosting region may constrain managed-broker options).
- **Downstream**: **Blocks 031** (scheduler enqueue), **041** (delivery retry/circuit-breaker), **016** (internal message authn implementation); informs 042 (delivery audit events).
- **External**: Broker/queue vendor documentation; hosting provider (per 073).

## Implementation Notes
- **Constraints**: Decision only — no code. Must remain cloud-portable and Docker-deployable; the envelope-authentication mechanism follows the chosen transport but MUST be expressible behind the queue interface and default to deny (SECURITY.md §3).
- **Anti-Patterns**: MUST NOT pick a broker implicitly via code; MUST NOT choose an at-most-once or non-durable transport for reminders; MUST NOT design unbounded retry (violates `NFR-1.5`); MUST NOT omit a DLQ with alerting.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Broker trade-off analysis over well-known messaging technologies (durability/DLQ/idempotency semantics) leans on broad ecosystem familiarity; no code is produced and no novel adversarial reasoning is required. The model MUST NOT resolve the choice — it prepares the scored matrix for human sign-off.
