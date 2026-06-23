# Requirement: DECISION — database engine + schema realization

## Metadata
- **ID**: REQ-DEC-069
- **Title**: Decide and document the database engine and schema realization for the Pingpals data model
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Critical
- **Classification**: Operational
- **Decision**: **RESOLVED — PostgreSQL.** Kept behind a repository interface (no unscoped escape hatch), cloud-portable (no proprietary engine lock-in), and also backs server-side revocable sessions (`SEC-1.3`). Human sign-off recorded via the project owner.

## Requirement
- **Description**: **RESOLVED.** The database engine is **PostgreSQL**, accessed strictly behind a repository interface so the choice stays swappable and cloud-portable; PostgreSQL also backs the server-side revocable session store. The decision is recorded with rationale against the criteria below, satisfies every listed constraint, and is signed off by a human (the project owner). Persistence code (issue 010) may now build against the PostgreSQL-backed repository interface. This issue produced NO implementation code itself and did not resolve the choice silently (`CLAUDE.md`: no new infrastructure decisions without explicit human sign-off).
- **Rationale**: The database underpins per-user isolation, encryption-at-rest, transactional cascade delete, and the tamper-evident audit log. Choosing it wrong (or implicitly) propagates risk through every data-handling control. `ARCHITECTURE.md` lists "Database engine and schema realization for the data model (§3, §5)" as `TO BE DECIDED`.
- **Design**: Not a UI feature; `DESIGN.md` does not apply beyond the constraint that no decision may weaken the privacy-by-default posture (`PRIV-1.13`).

## Scope
- **Applies To**: Both (the engine serves the Flask API; the schema realizes entities the SPA consumes)
- **Components**: Persistence layer (010), KMS/encryption integration (011), audit-log subsystem (012), erasure cascade (048), scheduler queries (031).
- **Actors**: Architects and the human approver (sign-off); no runtime actor — this is a decision artifact.
- **Data Classification**: Restricted (the engine will store contact PII, tokens, consent, audit logs).

## Security Context
- **Defense Layer**: Architecture (foundational infrastructure choice).
- **Threat(s) Addressed**: Cross-tenant data leakage from a poorly-isolatable store (CWE-639), unencrypted-at-rest Restricted data (CWE-311), partial/orphaned erasure from a non-transactional engine (GDPR Art. 17 risk), audit-log tampering. STRIDE: Information Disclosure, Tampering, Repudiation.
- **Trust Boundary**: The persistence boundary behind the Flask API; the engine choice determines how strongly per-user isolation and encryption can be enforced there.
- **Zero Trust Consideration**: Every query must carry the owning user as a non-optional constraint (`SEC-2.2`, ARCH Rule 4); the chosen engine and schema MUST make that enforceable and must not provide an unscoped escape hatch.

## Standards Alignment
- **OWASP ASVS**: V1.x (architecture), V8.x (data protection)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SC-28 (protection at rest), AC-4/AC-3 (isolation/access), AU-9 (audit-log protection)
- **NIST SP 800-207**: per-resource access enforcement; deny-by-default scoping
- **Regulatory**: GDPR Arts. 17 (erasure), 25 (data protection by design), 32 (security of processing)
- **Other**: `SEC-2.2`, `SEC-5.2`, `FR-1.3`, `PRIV-1.6`, `SEC-8.1`, ARCH `TO BE DECIDED`

## Evaluation Criteria (constraints any choice MUST satisfy)
1. **Per-user isolation** — supports strict per-user scoping with the owning user as a non-optional query constraint, with no unscoped read/write path (`SEC-2.2`).
2. **Encryption at rest** — Restricted data encryptable with AES-256-GCM or equivalent authenticated cipher, keys held in a managed key store, app holding no raw key material (`SEC-5.2`, `SEC-3.1`; coordinates with decision 072).
3. **Transactional cascade delete** — supports removing all of a contact's personal data, reminders, and outreach history in a single transaction (`FR-1.3`, `PRIV-1.6`).
4. **Tamper-evident audit support** — supports an append-only or hash-chained audit log with externally-anchorable head and segregated write path (`SEC-8.1`, `SEC-8.4`, `SEC-8.5`).
5. **Cloud-portable** — no hard dependency on a single cloud's proprietary engine (ARCH "many clouds"); runnable in the Docker-packaged deployment.
6. **Crypto-agility & rotation** — does not block algorithm/key rotation without code change to callers (`SEC-5.3`).
7. **Horizontal scalability by user shard** — supports the scheduler's per-user evaluation staying within its window and scaling across users (`NFR-1.1`).

## Candidate Options (evaluate, do NOT pick here)
- A managed/self-hostable relational engine (e.g. PostgreSQL-class) with row-level scoping and strong transactions.
- A relational engine with native/transparent encryption plus app-layer field encryption for Restricted columns.
- A document/NoSQL store (evaluate against transactional cascade and audit-chain constraints, which it may not meet).
- Append-only / ledger-style storage for the audit log specifically, paired with a primary store for entities (split-store option).

> Each option MUST be scored against all seven criteria with rationale. This issue does not select one.

## Acceptance Criteria
1. **AC-01**: Given the candidate options, when evaluated, then each is scored against all seven criteria with documented rationale.
2. **AC-02**: **RESOLVED** — the choice (PostgreSQL) is recorded in `ARCHITECTURE.md` (replacing the `TO BE DECIDED`) with rationale and is explicitly signed off by a human approver (the project owner).
3. **AC-03 (negative)**: Given any candidate that cannot satisfy a MUST criterion (isolation, encryption-at-rest, transactional cascade, or tamper-evident audit), when evaluated, then it is rejected and the reason is recorded.
4. **AC-04 (negative — no silent resolution)**: Given this issue, when worked, then no persistence implementation (010) is built and no engine is committed to code before human sign-off; until then code stays behind the persistence interface defaulting to the most restrictive option.

## Failure Behavior
- **On Invalid Input**: n/a (decision artifact).
- **On System Error**: Until resolved, dependents (010 and transitively 011, 012, 048, 031) stay blocked or behind the persistence interface defaulting to the most-restrictive option; no engine is assumed.
- **Alerting**: If a downstream issue is blocked waiting on this decision, flag it on the project board as decision-blocked.

## Test Strategy
- **Unit Tests**: n/a (no code). Provide a decision matrix artifact instead.
- **Integration Tests**: Optional spike/PoC validating that the front-runner can enforce per-user scoping, transactional cascade, and an append-only audit chain — results feed the decision, not production.
- **Security Tests**: Threat-review the front-runner against cross-tenant leakage and audit tampering.
- **Compliance Tests**: Confirm the choice supports GDPR Art. 17 cascade and Art. 32 at-rest encryption before sign-off.
- **Coverage Target**: n/a (decision issue).

## Dependencies
- **Upstream**: 053 (RoPA/DPIA context for data residency), decision 073 (hosting region may constrain managed-engine options), decision 072 (KMS for at-rest keys).
- **Downstream**: **Blocks 010** (persistence + user-scoping); transitively informs 011, 012, 048, 031.
- **External**: Database vendor/engine documentation; hosting provider (per 073).

## Implementation Notes
- **Constraints**: Decision only — no code. Must coexist with the `Docker`, cloud-portable packaging and the `TO BE DECIDED` KMS/region items; do not couple to a single cloud's proprietary service in MVP.
- **Anti-Patterns**: MUST NOT pick an engine implicitly by writing code against it (`CLAUDE.md`); MUST NOT choose a store that lacks transactional cascade or append-only audit support to "decide later"; MUST NOT defer encryption-at-rest to a future phase.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** This is an evaluation/trade-off and documentation task over well-known database technologies where broad ecosystem knowledge of engine capabilities is the main asset; no code is produced. The model MUST NOT resolve the choice — it prepares the scored matrix and options for human sign-off only.
