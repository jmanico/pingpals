# Requirement: DECISION — managed KMS vendor

## Metadata
- **ID**: REQ-DEC-072
- **Title**: Decide and document the managed key store (KMS) vendor for at-rest encryption and decrypt authority
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Security
- **Decision**: **STILL DEFERRED — `TO BE DECIDED`.** Remains open behind the key-store interface, defaulting to the most-restrictive deny-decrypt (no decrypt without an explicit per-adapter grant); the cloud/region is intentionally deferred cloud-agnostic (decision 073).

## Requirement
- **Description**: The team MUST decide and document the managed key store (KMS) vendor used to hold key material and perform encrypt/decrypt-unwrap for Restricted data (`ARCHITECTURE.md` `TO BE DECIDED`). The choice MUST keep raw key material out of application code, support partitioned/purpose-scoped decrypt authority, support key rotation and crypto-agility, and sit behind the key-store interface so it stays cloud-portable. The decision MUST be recorded with rationale against the criteria below, satisfy every listed constraint, and be signed off by a human before the encryption-at-rest implementation (issue 011) is built. This issue produces NO implementation code and MUST NOT silently resolve the choice (`CLAUDE.md`).
- **Rationale**: OAuth tokens and Restricted data MUST be encrypted at rest with keys in a managed key store, and application code MUST NOT hold raw key material (`SEC-3.1`, `SEC-5.2`). The decrypt/unwrap capability is itself a sensitive grant requiring per-adapter, purpose-scoped partitioning with no single application-wide decrypt role (SECURITY.md §5). `ARCHITECTURE.md` lists KMS selection as `TO BE DECIDED`.
- **Design**: Not a UI feature; `DESIGN.md` does not apply.

## Scope
- **Applies To**: API/backend
- **Components**: KMS encryption-at-rest (011), persistence (010), OAuth provider adapters (022), audit log of decrypt invocations (012), crypto inventory (006), backups encryption (`SEC-5.6`).
- **Actors**: Backend components and integration adapters (each least-privilege decrypt grant); human approver.
- **Data Classification**: Restricted (tokens, contact PII, consent, audit) — all protected by these keys.

## Security Context
- **Defense Layer**: Architecture / Secrets & key handling.
- **Threat(s) Addressed**: Raw key material in app memory/code (CWE-321/CWE-798), over-broad decrypt authority letting one component read another's tokens (CWE-269 privilege misuse), unrotated long-lived keys (CWE-324), keys stored alongside ciphertext in backups (CWE-312). STRIDE: Information Disclosure, Elevation of Privilege.
- **Trust Boundary**: The KMS is the key-material trust boundary; app code invokes encrypt/decrypt but never extracts raw keys.
- **Zero Trust Consideration**: Decrypt authority is least-privilege, purpose-scoped, partitioned per adapter, and fails closed; any principal without an explicit grant is denied, and every decrypt/denial is audited (SECURITY.md §5, `SEC-8.1`).

## Standards Alignment
- **OWASP ASVS**: V6.x (cryptography / key management)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SC-12/SC-13 (key establishment/cryptographic protection), SC-28 (at rest), AU-2 (audit decrypt use)
- **NIST SP 800-207**: least-privilege, deny-by-default decrypt authority
- **Regulatory**: GDPR Art. 32 (security of processing)
- **Other**: `SEC-3.1`, `SEC-5.2`, `SEC-5.3`, `SEC-5.5`, `SEC-5.6`, FIPS 203 readiness (`SEC-5.4`, coordinate with decision 074)

## Evaluation Criteria (constraints any choice MUST satisfy)
1. **No raw key material in app** — keys never leave the KMS; app code performs encrypt/decrypt-unwrap calls only (`SEC-3.1`).
2. **Partitioned, purpose-scoped decrypt authority** — supports per-component/per-adapter grants so no single application-wide decrypt role exists and one adapter cannot decrypt another's token reference (SECURITY.md §5).
3. **Key rotation** — supports rotation of long-lived keys without code changes to callers, enabling future PQ migration (`SEC-5.3`, `SEC-5.4`).
4. **Crypto-agility** — algorithm/key references configurable and rotatable behind the key-store interface (`SEC-5.3`).
5. **Audit of decrypt** — every decrypt/unwrap invocation and denial is recordable in the tamper-evident audit log, excluding plaintext (`SEC-8.1`, `SEC-8.2`).
6. **Backup key separation** — supports encrypting backups with the same managed keys without storing keys alongside ciphertext (`SEC-5.6`).
7. **Cloud-portable behind interface** — usable behind the abstract key-store interface so the vendor is swappable; not hard-wired into business logic (ARCH "many clouds").

## Candidate Options (evaluate, do NOT pick here)
- A cloud-managed KMS (envelope encryption + per-key IAM grants) — evaluate against cloud-portability and per-adapter partitioning.
- A vendor-neutral / self-hostable secrets-and-key manager (e.g. a transit/encryption-as-a-service engine) — evaluate against managed-rotation and audit.
- A hardware-backed HSM-as-a-service — evaluate against cost, portability, and crypto-agility.

> Each option MUST be scored against all seven criteria with rationale. This issue does not select one.

## Acceptance Criteria
1. **AC-01**: Given the candidate options, when evaluated, then each is scored against all seven criteria with documented rationale.
2. **AC-02**: Given the evaluation, when a choice is recommended, then it is recorded in `ARCHITECTURE.md` (replacing the `TO BE DECIDED`) with rationale and explicit human sign-off, and the chosen vendor's keys are added to the crypto inventory (`SEC-5.5`, issue 006).
3. **AC-03 (negative)**: Given any candidate that exposes raw key material to app code, cannot partition decrypt authority, or cannot rotate keys, when evaluated, then it is rejected and the reason recorded.
4. **AC-04 (negative — no silent resolution)**: Given this issue, when worked, then no at-rest-encryption implementation (011) is built and no vendor is committed before human sign-off; until then crypto stays behind the key-store interface defaulting to deny (no decrypt without an explicit grant).

## Failure Behavior
- **On Invalid Input**: n/a (decision artifact).
- **On System Error**: Until resolved, dependent 011 stays blocked or behind the key-store interface defaulting to the most-restrictive (deny decrypt) option; no vendor assumed.
- **Alerting**: Flag 011 as decision-blocked on the board while this is open.

## Test Strategy
- **Unit Tests**: n/a (no code). Provide a decision matrix artifact.
- **Integration Tests**: Optional spike validating envelope encrypt/decrypt, per-grant partitioning, rotation, and audit of a decrypt call on the front-runner; results feed the decision only.
- **Security Tests**: Threat-review the front-runner against over-broad decrypt authority and key-alongside-ciphertext backup risk.
- **Compliance Tests**: Confirm decrypt invocations are auditable and the choice supports `SEC-5.6` key-separated backups.
- **Coverage Target**: n/a (decision issue).

## Dependencies
- **Upstream**: 006 (crypto inventory), decision 073 (region may constrain managed-KMS options), decision 069 (engine determines at-rest integration), decision 074 (PQ readiness coordination).
- **Downstream**: **Blocks 011** (KMS encryption-at-rest); informs 010, 022, 042, and backups (`SEC-5.6`).
- **External**: KMS/HSM vendor documentation; hosting provider (per 073).

## Implementation Notes
- **Constraints**: Decision only — no code. Decrypt-authority partitioning MUST be expressible behind the key-store interface and default to deny while the vendor is `TO BE DECIDED` (SECURITY.md §5). Keep cloud-portable; coordinate PQ-readiness with decision 074.
- **Anti-Patterns**: MUST NOT pick a KMS implicitly via code; MUST NOT design a single application-wide decrypt role; MUST NOT store decryption keys alongside ciphertext in backups (`SEC-5.6`); MUST NOT defer audit of decrypt invocations.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** KMS vendor trade-off analysis over standard key-management offerings (envelope encryption, IAM grants, rotation) is breadth-of-ecosystem evaluation and documentation; no code is produced. The model MUST NOT resolve the choice — it prepares the scored matrix for human security sign-off, ensuring per-adapter decrypt partitioning is graded on every option.
