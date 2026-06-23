# Requirement: KMS-backed encryption at rest with partitioned decrypt authority

## Metadata
- **ID**: REQ-BE-011
- **Title**: Key-store interface, AES-256-GCM envelope encryption, and per-component/per-adapter decrypt partitioning
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Critical
- **Classification**: Security

## Requirement
- **Description**: The backend MUST encrypt all Restricted data at rest using AES-256-GCM (or an equivalent authenticated cipher) under keys held in a managed key store, behind a key-store interface; application code MUST NOT hold raw key material. Decrypt/unwrap authority MUST be least-privilege, purpose-scoped, and partitioned: each backend component MAY decrypt only the class of Restricted data it processes, and each integration adapter MAY decrypt only its own provider's token(s) — the capability MUST NOT be able to resolve another adapter's token reference or another data class, there MUST NOT be a single application-wide decrypt role, and any principal without an explicit grant MUST be denied (default deny). Every decrypt/unwrap invocation and every denial MUST be recorded in the tamper-evident audit log, attributing the calling component and purpose and excluding plaintext. Backups, snapshots, and any other copies of Restricted data MUST be encrypted with the same cipher and managed keys, MUST NOT store decryption keys alongside the ciphertext, and are within the erasure/retention and breach scope. The KMS vendor is `TO BE DECIDED` (DECISION 072); the scoping MUST be expressed behind the interface and default to deny until resolved.
- **Rationale**: Anchored in `SEC-3.1` (encrypt at rest, no raw keys in app), `SEC-5.2` (AES-256-GCM), `SEC-5.6` (encrypted, key-separated backups), and SECURITY.md §5's decrypt-partition rule. The right to invoke decrypt is itself a sensitive grant — holding it yields plaintext even though raw key material never leaves the KMS — so a single app-wide decrypt role would let any compromised component read every user's tokens; partitioning contains blast radius (ARCH Rule 7, NIST SP 800-207 least privilege).
- **Design**: No user-facing surface. Supports the "integrations off by default / minimum scopes" privacy posture (`PRIV-1.13`) by ensuring provider tokens are isolated.

## Scope
- **Applies To**: API
- **Components**: Flask API service — key-store/KMS adapter interface, envelope-encryption helper, per-component/per-adapter decrypt-grant model, backup encryption contract. Consumed by the persistence layer (issue 010) and each integration adapter.
- **Actors**: Backend components (API, Scheduler, Delivery worker), integration adapters (Google People, transactional email) — each a distinct principal with a scoped grant; operators provisioning keys.
- **Data Classification**: Restricted (`ProviderToken`, contact personal data, consent records, audit data at rest); Confidential (key references). Per §3.

## Security Context
- **Defense Layer**: Cryptographic storage + Authorization (partitioned decrypt capability).
- **Threat(s) Addressed**: Plaintext exposure of tokens/PII at rest (CWE-311/312), over-broad decrypt authority enabling lateral plaintext access (CWE-269 improper privilege management), key-with-ciphertext co-location in backups (CWE-321/798), unencrypted snapshot leakage. STRIDE: Information Disclosure, Elevation of Privilege.
- **Trust Boundary**: The encrypted-at-rest / KMS layer — secrets and tokens flow one way into it (ARCH Rule 5); the decrypt capability is a guarded boundary partitioned per principal so crossing it for a sibling adapter's data is denied.
- **Zero Trust Consideration**: No component is trusted to decrypt broadly; each must present an explicit, purpose-scoped grant, and an indeterminate/absent grant fails closed to deny. Per-user token scoping (`SEC-2.2`) applies unchanged on top of the partitioning.

## Standards Alignment
- **OWASP ASVS**: V6.2 (cryptographic algorithms), V6.4 (secret management), V8.3 (data at rest)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SC-12/SC-13 (key management & cryptographic protection), SC-28 (protection of information at rest), AC-6 (least privilege), AU-2 (auditable events)
- **NIST SP 800-207**: least-privilege, per-principal authorization of the decrypt capability
- **Regulatory**: GDPR Art. 32 (encryption at rest), Art. 5(1)(f) integrity/confidentiality
- **Other**: SECURITY.md §5; ARCH Rules 5 & 7; `SEC-3.1`, `SEC-5.2`, `SEC-5.6`, `SEC-8.1`, `SEC-8.2`, FIPS-aligned crypto agility (`SEC-5.3`)

## Acceptance Criteria
1. **AC-01**: Given Restricted data is persisted, when written, then it is stored as AES-256-GCM (or equivalent authenticated) ciphertext under a managed-key-store key, and application code never possesses raw key material (`SEC-3.1`, `SEC-5.2`).
2. **AC-02 (verbatim `SEC-5.6`)**: Given a stored backup of Restricted data, when restore is attempted without the managed key store, then it is unreadable, and a stored backup with no associated managed key is rejected rather than retained in plaintext.
3. **AC-03 (negative, verbatim SECURITY.md §5 decrypt-partition clause)**: Given a component lacking the grant for a data class, or an adapter attempting to decrypt a sibling adapter's token reference, when it calls decrypt/unwrap, then it receives a denied response (not plaintext), an audit entry records the denial, and no single role can decrypt every Restricted data class.
4. **AC-04**: Given any decrypt/unwrap invocation, when it succeeds, then a tamper-evident audit entry records the calling component and purpose and contains no plaintext (`SEC-8.1`, `SEC-8.2`).
5. **AC-05 (negative)**: Given a principal with no explicit decrypt grant, when it requests decrypt, then it is denied by default (no implicit/app-wide decrypt role exists).
6. **AC-06**: Given the KMS vendor is undecided, when crypto operations run, then they go through the key-store interface and default to deny on any indeterminate authorization, with algorithm/key references configurable and rotatable without changing callers (`SEC-5.3`, DECISION 072).

## Failure Behavior
- **On Invalid Input**: A decrypt request for an out-of-scope data class/adapter is denied (not plaintext) and audited.
- **On System Error**: Fail closed — a key-store outage or indeterminate grant denies the operation; decrypted key material MUST NOT be cached to absorb outages under this issue (that is a SECURITY.md §5 / `SEC-3.1` decision, out of scope here).
- **Alerting**: Decrypt denials and key-store unavailability raise security/operational alerts; a backup found without an associated managed key raises a high-severity alert.

## Test Strategy
- **Unit Tests**: Envelope encrypt/decrypt round-trip; grant model accepts only the matching component/adapter and denies others; denial path returns no plaintext and emits an audit call.
- **Integration Tests**: Adapter A cannot resolve/decrypt adapter B's token reference; per-component data-class partitioning enforced end to end; rotation swaps key reference without code change.
- **Security Tests**: Attempt cross-adapter and cross-class decrypt; assert backups unreadable without the key store; SAST rule banning raw key material in app code and keys co-located with ciphertext.
- **Compliance Tests**: Cryptographic inventory entry (`SEC-5.5`) for algorithms/key locations/rotation; audit evidence of decrypt invocations and denials.
- **Coverage Target**: ≥ 80% branch coverage of the key-store adapter and grant model.

## Dependencies
- **Upstream**: 007 (Flask skeleton), 010 (persistence — stores ciphertext + key references), 012 (audit log — receives decrypt/denial events), 072 (DECISION: KMS vendor).
- **Downstream**: Integration adapter issues (Google People, email — each scoped to its own token), Privacy/DSR erasure (`PRIV-1.6` purges tokens), backup/retention issues (`SEC-5.6`, `PRIV-1.9`).
- **External**: Managed key store / KMS (vendor `TO BE DECIDED`, DECISION 072), behind the interface defaulting to deny.

## Implementation Notes
- **Constraints**: KMS vendor `TO BE DECIDED` — express the grant partitioning behind the interface and default to deny; do not resolve the vendor here. Crypto agile: algorithm/key references configurable and rotatable without caller changes (`SEC-5.3`). Maintain the cryptographic inventory (`SEC-5.5`).
- **Anti-Patterns**: MUST NOT create a single application-wide decrypt role; MUST NOT let an adapter resolve another adapter's token reference; MUST NOT hold raw key material in app code; MUST NOT store decryption keys alongside ciphertext in backups; MUST NOT log plaintext or key material in audit/decrypt events; MUST NOT introduce in-memory key caching under this issue.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Decrypt-authority partitioning is a subtle, high-blast-radius authorization control where an over-broad grant silently undoes tenant and adapter isolation; favor the model with stronger reasoning about capability scoping and fail-closed defaults. Mandatory human security review of the grant model and the audit-on-decrypt path before merge.
