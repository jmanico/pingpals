# Requirement: Crypto-agility configuration and cryptographic inventory

## Metadata
- **ID**: REQ-FND-006
- **Title**: Configurable, rotatable crypto algorithm/key-reference layer plus a maintained cryptographic inventory
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Medium
- **Classification**: Security

## Requirement
- **Description**: The system MUST be **crypto-agile**: every cryptographic algorithm choice and key reference used for Restricted-data protection (encryption at rest, token/credential wrapping, hashing/signing for the audit chain) MUST be **configurable and rotatable without code changes to callers**, expressed behind a stable crypto/key-store interface. The system MUST also maintain a **cryptographic inventory** recording, for each crypto asset, the algorithm, key length, key location/reference, and rotation status. The interface MUST default to the most restrictive option while the KMS vendor is `TO BE DECIDED`, and MUST fail closed if an algorithm/key reference is unresolved or untrusted.
- **Rationale**: `SEC-5.3` requires crypto-agility (algorithms and key references configurable/rotatable without caller changes); `SEC-5.5` requires a cryptographic inventory for cryptographic asset management. Agility is the precondition for migrating to hybrid post-quantum key exchange (`SEC-5.4`, future) and for routine rotation of long-lived secrets without re-engineering callers. The inventory is what rotation, audit, and breach response (`PRIV-1.14`) read from.
- **Design**: No user-facing surface. This is the cryptographic substrate beneath Persistence/KMS in `ARCHITECTURE.md`; callers (token storage, at-rest encryption, audit-log hash chain) depend on the interface, never on a concrete algorithm or key.

## Scope
- **Applies To**: API
- **Components**: Crypto/key-store interface (in the API module's Persistence/KMS package per 001); cryptographic-inventory record/registry; consumers — token storage (provider tokens), Restricted-data at-rest encryption, audit-log integrity (`SEC-8.x`).
- **Actors**: Backend services (callers of encrypt/decrypt/sign); operators performing rotation; auditors reading the inventory.
- **Data Classification**: Restricted (the interface protects Restricted data and secret/key material; the inventory itself is Internal but MUST NOT contain key material).

## Security Context
- **Defense Layer**: Architecture / Cryptography (agility + asset management)
- **Threat(s) Addressed**: Algorithm obsolescence and inability to rotate (CWE-327 use of broken/risky crypto if pinned), hard-coded key references, blind spots in crypto asset management; "harvest now, decrypt later" prepared against via future PQ migration (`SEC-5.4`). STRIDE: Information Disclosure, Tampering.
- **Trust Boundary**: The crypto/key-store interface — application code holds NO raw key material (`SEC-3.1`); only the managed key store performs key operations behind the interface.
- **Zero Trust Consideration**: An algorithm or key reference that cannot be resolved or whose trust/availability is indeterminate MUST fail closed (deny the operation) rather than fall back to a weaker or default algorithm (`SEC-2.3`, `NFR-1.6`).

## Standards Alignment
- **OWASP ASVS**: V6.2 (algorithm agility), V6.4 (secret/key management)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SC-12 (key establishment & management), SC-13 (cryptographic protection)
- **NIST SP 800-207**: least-privilege, fail-closed crypto operations behind the boundary
- **Regulatory**: GDPR Art. 32 (security of processing) supported by managed, rotatable encryption
- **Other**: `SEC-5.2` (AES-256-GCM/authenticated cipher), `SEC-5.3`, `SEC-5.5`, `SEC-5.4` (future PQ — DECISION 074), `SEC-3.1`, SECURITY §5

## Acceptance Criteria
1. **AC-01**: Given the crypto interface, when the configured at-rest algorithm or key reference is changed (e.g. rotated), then no caller (token storage, at-rest encryption, audit hashing) requires a code change to keep working. *(verifies `SEC-5.3` "without code changes to callers".)*
2. **AC-02**: Given the cryptographic inventory, when inspected, then each crypto asset records algorithm, key length, key location/reference, and rotation status. *(verifies `SEC-5.5`.)*
3. **AC-03**: Given Restricted data at rest, when encrypted via the interface, then an AES-256-GCM (or equivalent authenticated) cipher with a managed key is used and no raw key material is held by application code. *(maps `SEC-5.2`, `SEC-3.1`.)*
4. **AC-04 (negative)**: Given an unresolved, missing, or untrusted algorithm/key reference, when an encrypt/decrypt/sign operation is requested, then the operation fails closed (denied) and never falls back to a default or weaker algorithm.
5. **AC-05 (negative)**: Given the cryptographic inventory or any log, when inspected, then it contains no raw key material or secret (`SEC-8.2`, ARCH Rule 5).
6. **AC-06**: Given the KMS vendor is `TO BE DECIDED`, when the interface is reviewed, then the algorithm/key scoping is expressed behind the key-store interface and defaults to deny, with no vendor SDK hard-committed (defers to DECISION for KMS).

## Failure Behavior
- **On Invalid Input**: A request naming an unknown/disallowed algorithm or unresolvable key reference is rejected, not silently downgraded.
- **On System Error**: Fail closed — a key-store outage or unresolved key reference denies the crypto operation and any dependent security decision (`SEC-2.3`, `NFR-1.6`); no Restricted data is served from a failed-closed path, and decrypted key material MUST NOT be cached to absorb the outage (that is owned by SECURITY §5 / `SEC-3.1`, not introduced here).
- **Alerting**: A rotation overdue per the inventory, or a spike in fail-closed crypto denials, SHOULD raise an operational alert (destination `TO BE DECIDED`).

## Test Strategy
- **Unit Tests**: Algorithm/key resolution is config-driven; switching the configured algorithm or key reference changes behavior with no caller edits; unknown algorithm/unresolved key reference fails closed.
- **Integration Tests**: Encrypt/decrypt a Restricted record and verify round-trip through the interface against the (interface-mocked) key store; simulate a rotation and confirm callers are unaffected; simulate key-store outage and confirm fail-closed.
- **Security Tests**: Confirm no raw key material appears in application memory dumps, logs, or the inventory; confirm authenticated cipher (GCM tag) integrity rejects tampered ciphertext.
- **Compliance Tests**: The cryptographic inventory is generated and retained with algorithm/key-length/location/rotation fields for audit (`SEC-5.5`); evidence that rotation requires no caller code change.
- **Coverage Target**: ≥ 80% branch coverage of the crypto/key-store interface and inventory module.

## Dependencies
- **Upstream**: 001 (Persistence/KMS package location). Key-store/KMS vendor selection is `TO BE DECIDED` (DECISION issue 074 referenced for PQ; KMS-vendor DECISION tracked separately) — keep behind the interface.
- **Downstream**: Provider-token storage, Restricted-data at-rest encryption, audit-log integrity (`SEC-8.x`), backup encryption (`SEC-5.6`), and any future PQ migration (`SEC-5.4`).
- **External**: Managed key store / KMS (`TO BE DECIDED`); the interface defaults to deny and abstracts the vendor.

## Implementation Notes
- **Constraints**: Application code holds NO raw key material — only the managed key store performs key ops (`SEC-3.1`). Default to the most restrictive option while the KMS is undecided. PQ hybrid key exchange (`SEC-5.4`) is FUTURE and out of scope here; design the agility layer so it can later carry an `X25519 + ML-KEM-768` (FIPS 203) suite without caller changes, and reference DECISION 074 rather than implementing PQ now.
- **Anti-Patterns**: MUST NOT hard-code an algorithm or key reference in callers; MUST NOT fall back to a default/weaker algorithm on resolution failure (fail closed, `SEC-2.3`); MUST NOT log or inventory raw key material/secrets (`SEC-8.2`); MUST NOT commit a concrete KMS vendor SDK as a required dependency (`TO BE DECIDED`); MUST NOT cache decrypted key material to mask a key-store outage under this issue (`NFR-1.6` defers that to `SEC-3.1`).
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Crypto-agility and fail-closed key handling are security-critical and subtly error-prone (downgrade attacks, key-reference confusion, cache-the-plaintext temptations); favor the strongest adversarial-reasoning model on cryptographic edge cases. Mandatory human security review before merge; keep the interface PQ-ready (DECISION 074) without resolving the KMS choice.
