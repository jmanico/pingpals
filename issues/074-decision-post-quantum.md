# Requirement: DECISION — hybrid post-quantum key exchange support

## Metadata
- **ID**: REQ-DEC-074
- **Title**: Decide and document hybrid post-quantum key-exchange support and PQ-migration readiness
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Medium
- **Classification**: Security
- **Decision**: **RESOLVED — migration-ready classical baseline.** The posture is **TLS 1.3 + crypto-agility (`SEC-5.3`) + long-lived-secret rotation (`SEC-5.4`)**. **NO post-quantum algorithm is committed now**; a hybrid PQ scheme (e.g. X25519 + ML-KEM-768 per FIPS 203) remains adoptable later **without caller code changes**. Human sign-off recorded via the project owner.

## Requirement
- **Description**: **RESOLVED.** The adopted posture is a **migration-ready classical baseline**: TLS 1.3 for key establishment, full crypto-agility, and rotation of all long-lived stored secrets, with **no post-quantum algorithm committed at this time**. A hybrid (classical + PQ) construction MAY be adopted later as platform/provider support matures, swappable behind the crypto-agility surface **without code changes to callers**; PQ-only constructions are excluded. The readiness assessment is recorded with rationale and signed off by a human (the project owner). This issue produced NO implementation code itself and did not resolve the choice silently (`CLAUDE.md`).
- **Rationale**: `SEC-5.4` states the system SHOULD adopt hybrid PQ key exchange where the platform and providers support it, and that long-lived stored secrets MUST be protected with rotation to enable migration to post-quantum algorithms. Because availability hinges on the chosen platform (decisions 071/072/073), this is a readiness decision, not an immediate implementation.
- **Design**: Not a UI feature; `DESIGN.md` does not apply.

## Scope
- **Applies To**: API/backend (transport/key-establishment and at-rest key handling)
- **Components**: TLS/transport layer, KMS key handling (011 / decision 072), crypto inventory (006), crypto-agility surface (`SEC-5.3`).
- **Actors**: Architects/security; human approver; no runtime actor.
- **Data Classification**: Restricted (long-lived secrets, tokens protected under these keys).

## Security Context
- **Defense Layer**: Architecture / Cryptography (forward-looking).
- **Threat(s) Addressed**: "Harvest now, decrypt later" against classical key exchange (future quantum adversary, CWE-327 weak-by-future-standard), inability to migrate due to non-rotatable long-lived secrets (CWE-324). STRIDE: Information Disclosure (future).
- **Trust Boundary**: The key-establishment boundary (transport and KMS); the decision determines whether hybrid PQ protects it now or whether the system stays migration-ready.
- **Zero Trust Consideration**: Crypto is treated as needing future replacement; the decision ensures crypto-agility (`SEC-5.3`) so the algorithm is swappable without trusting it to remain strong indefinitely.

## Standards Alignment
- **OWASP ASVS**: V6.x (cryptography)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SC-12 (key establishment), SC-13 (cryptographic protection)
- **NIST SP 800-207**: n/a
- **Regulatory**: GDPR Art. 32 (state-of-the-art security of processing)
- **Other**: FIPS 203 (ML-KEM), RFC 8446 (TLS 1.3), `SEC-5.3`, `SEC-5.4`, `SEC-5.5`

## Evaluation Criteria (constraints any choice MUST satisfy)
1. **Platform/provider support** — assess whether the chosen hosting (073), KMS (072), push (071), and TLS termination support hybrid PQ key exchange today (`SEC-5.4`).
2. **Hybrid construction** — if adopted, use a hybrid (classical + PQ, e.g. X25519 + ML-KEM-768) so security is no weaker than the classical baseline (FIPS 203).
3. **Crypto-agility** — the algorithm/key references are configurable and rotatable without code changes to callers, whether or not PQ is adopted now (`SEC-5.3`).
4. **Long-lived secret rotation** — all long-lived stored secrets are rotation-ready so a later PQ migration is feasible (`SEC-5.4`).
5. **Inventory** — the chosen/planned algorithms and their PQ-migration status are recorded in the cryptographic inventory (`SEC-5.5`, issue 006).
6. **Fail-safe default** — if PQ is not adopted now, the baseline remains TLS 1.3 with classical key exchange plus documented migration readiness (no weaker fallback).

## Candidate Options (evaluate, do NOT pick here)
- Adopt hybrid PQ key exchange now where the platform supports it; classical-only where it does not.
- Defer PQ adoption but enforce full crypto-agility and long-lived-secret rotation now (migration-ready posture).
- Per-channel decision (e.g. transport vs. at-rest key wrapping) based on each provider's PQ readiness.

> Each option MUST be assessed against all six criteria with rationale. This issue does not select one.

## Acceptance Criteria
1. **AC-01**: Given the candidate options, when evaluated against platform/provider PQ support (from decisions 071/072/073), then each is assessed against all six criteria with documented rationale.
2. **AC-02**: **RESOLVED** — the posture (migration-ready classical baseline: TLS 1.3 + crypto-agility + long-lived-secret rotation, no PQ algorithm committed now) is recorded in `ARCHITECTURE.md`/`SECURITY.md` with rationale and explicit human sign-off (the project owner), and the crypto inventory (006) reflects the algorithms and PQ-migration status.
3. **AC-03 (negative)**: Given any option that adopts a PQ-only (non-hybrid) construction or that leaves long-lived secrets non-rotatable, when evaluated, then it is rejected and the reason recorded.
4. **AC-04 (negative — no silent resolution)**: Given this issue, when worked, then no PQ implementation is committed and no algorithm is hard-wired before human sign-off; until then crypto stays agile behind the interface with classical TLS 1.3 as the documented baseline (no weaker fallback).

## Failure Behavior
- **On Invalid Input**: n/a (decision artifact).
- **On System Error**: Until resolved, the system stays on the migration-ready classical baseline (TLS 1.3 + crypto-agility + rotation); no PQ algorithm is assumed and no dependent is unblocked into a non-agile path.
- **Alerting**: Re-evaluate when platform/provider PQ support changes; flag the crypto inventory (006) for review on any such change.

## Test Strategy
- **Unit Tests**: n/a (no code). Provide a readiness-assessment artifact.
- **Integration Tests**: Optional spike confirming the chosen platform/KMS can negotiate/wrap with a hybrid PQ scheme if adopted; results feed the decision only.
- **Security Tests**: Confirm crypto-agility (algorithm swap without caller code change) on the existing baseline.
- **Compliance Tests**: Confirm long-lived secrets are rotation-ready and recorded in the crypto inventory (`SEC-5.5`).
- **Coverage Target**: n/a (decision issue).

## Dependencies
- **Upstream**: 006 (crypto inventory), decisions 071 (push provider), 072 (KMS), 073 (hosting) — their PQ support gates feasibility.
- **Downstream**: Informs 011 (at-rest key handling) and the transport/TLS configuration; no code issue is hard-blocked, but all rely on crypto-agility staying intact.
- **External**: Platform/provider PQ-support roadmaps; FIPS 203 / ML-KEM tooling.

## Implementation Notes
- **Constraints**: Decision only — no code. Adoption is conditional on provider support (`SEC-5.4` is a SHOULD); the non-negotiable part is crypto-agility and long-lived-secret rotation now. Any PQ adoption MUST be hybrid (never PQ-only).
- **Anti-Patterns**: MUST NOT hard-wire a single key-exchange algorithm into callers; MUST NOT deploy a PQ-only construction; MUST NOT leave long-lived secrets non-rotatable; MUST NOT claim PQ support without confirming provider capability.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Post-quantum readiness assessment requires careful reasoning about hybrid constructions, harvest-now-decrypt-later risk, and crypto-agility/migration correctness where a subtle misjudgment (e.g. endorsing PQ-only) is security-relevant; the stronger model is preferred even though no code is produced. The model MUST NOT resolve the choice — it prepares the readiness assessment for human security sign-off.
