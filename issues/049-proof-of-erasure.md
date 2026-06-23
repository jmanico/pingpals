# Requirement: Surviving, PII-free proof-of-erasure record

## Metadata
- **ID**: REQ-PRIV-049
- **Title**: Tamper-evident proof-of-action record for erasure and DSR fulfilment, excluded from the cascade
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Compliance

## Requirement
- **Description**: Every erasure (`PRIV-1.6`, issue 048) and every DSR fulfilment MUST produce a proof-of-action record in the tamper-evident audit log (`SEC-8.1`, 012) that is explicitly excluded from the `PRIV-1.6` cascade and therefore survives it. This record MUST contain no contact personal data: only a pseudonymous subject reference, the DSR type, the set of stores purged, the requesting principal, and the server-authoritative completion timestamp. The erasure MUST fail closed: it MUST NOT be reported complete until this record is durably committed to the tamper-evident log; if the record cannot be written or its tamper-evidence (hash chain) cannot be preserved, the erasure MUST abort rather than proceed without surviving proof.
- **Rationale**: GDPR Article 5(2) accountability requires the controller to *demonstrate* that an erasure happened — but the demonstration cannot itself retain the erased PII. The resolution is a pseudonymous, surviving proof that is carved out of the cascade. Without the fail-closed gate, an erasure could "succeed" with no durable evidence, defeating accountability. This is the data-of-record behind `PRIV-1.16`.
- **Design**: The proof record is internal evidence with no UI surface beyond a DSR confirmation in the gentle royal voice (`DESIGN.md` §6); the confirmation appears only after the proof is durably committed.

## Scope
- **Applies To**: API
- **Components**: Privacy/DSR subsystem + tamper-evident audit log (012); proof-write gate sits at the end of the erasure executor (048).
- **Actors**: Erasure executor (writer); requesting principal (recorded, not actor of the proof); auditor (read-only verifier).
- **Data Classification**: Restricted (audit log) but the proof record itself carries no contact PII — only a pseudonymous subject reference.

## Security Context
- **Defense Layer**: Architecture (carve-out + fail-closed commit) + Logging/audit integrity
- **Threat(s) Addressed**: Repudiation of erasure (no surviving evidence, CWE-778 insufficient logging), accidental re-introduction of PII into the surviving record, tamper/rollback of the proof. STRIDE: Repudiation, Tampering, Information Disclosure.
- **Trust Boundary**: Audit subsystem — the proof is written through the same tamper-evident path as 012 and is anchored separately (`SEC-8.5`) so it cannot be silently rewritten; it is explicitly outside the erasure cascade's reach.
- **Zero Trust Consideration**: The erasure does not trust an in-memory "done" flag; completion is only asserted after the durable, hash-chain-preserving proof commit is confirmed.

## Standards Alignment
- **OWASP ASVS**: V7.x (logging integrity, no sensitive data in logs)
- **OWASP AISVS**: n/a (no AI component)
- **NIST SP 800-53**: AU-9 (protection of audit information), AU-10 (non-repudiation), SI-12 (information handling)
- **NIST SP 800-207**: explicit, verifiable accountability of a privileged action
- **Regulatory**: GDPR Arts. 5(2) (accountability), 17 (erasure), 30 (records of processing — cross-ref 053)
- **Other**: `PRIV-1.16`, `PRIV-1.6`, `SEC-8.1`, `SEC-8.2`, `SEC-8.5`

## Acceptance Criteria
1. **AC-01 (verbatim `PRIV-1.16`)**: Given an erasure, when it completes, then a post-deletion query returns no contact personal data for the subject (`PRIV-1.6`) yet a PII-free, tamper-evident proof-of-erasure record for that subject remains retrievable and its hash chain validates.
2. **AC-02**: Given a proof-of-action record, when inspected, then it contains only a pseudonymous subject reference, the DSR type, the set of stores purged, the requesting principal, and the server-authoritative completion timestamp — and no contact personal data.
3. **AC-03 (negative)**: Given the proof record cannot be durably committed or its hash chain cannot be preserved, when the erasure runs, then the erasure aborts and is NOT reported complete (fail closed).
4. **AC-04 (negative)**: Given an attempt to delete or rewrite a proof record as part of the `PRIV-1.6` cascade, when processed, then the proof is excluded from the cascade and survives, and any tamper attempt is detected by the chain verifier (012 / `SEC-8.5`).

## Failure Behavior
- **On Invalid Input**: An erasure whose subject cannot be resolved produces no proof and no deletion (rejected upstream in 048).
- **On System Error**: Fail closed — if the audit log is unavailable or the chain cannot be preserved, abort the erasure; do not report completion without surviving proof.
- **Alerting**: A failed proof commit, or a detected tamper/gap involving a proof record, raises a tamper + compliance alert.

## Test Strategy
- **Unit Tests**: Proof-record construction (PII-free field set), pseudonymous subject reference derivation, completion-gating logic.
- **Integration Tests**: Run an erasure; assert subject PII is gone (048) while a valid, chain-verifying proof remains; assert the proof survives a subsequent cascade pass (maps to TEST-1.4).
- **Security Tests**: Force the proof write to fail and assert the erasure aborts (fail closed); tamper a historical proof entry and assert the verifier detects it (`SEC-8.5`).
- **Compliance Tests**: Automated evidence that every erasure/DSR fulfilment has a surviving, PII-free, chain-valid proof (Art. 5(2)).
- **Coverage Target**: ≥ 80% branch coverage of the proof-write + completion-gate module.

## Dependencies
- **Upstream**: 012 (tamper-evident audit log + chain verification), 048 (erasure cascade — proof gates its completion).
- **Downstream**: 050 (DSR endpoints rely on proof for fulfilment evidence), 051 (accountability retention preserves proof records), 053 (RoPA/DPIA cite the proof mechanism as Art. 5(2) evidence).
- **External**: None (audit anchor store per 012; KMS via 011 interface).

## Implementation Notes
- **Constraints**: Proof write shares the tamper-evident chain of 012 and is committed before completion is asserted; pseudonymous subject reference MUST NOT be reversible to contact PII within the record. Server-authoritative timestamp only (`SEC-8.3`).
- **Anti-Patterns**: MUST NOT embed contact PII (name, phone, email, notes) in the proof; MUST NOT report erasure complete before the proof is durable; MUST NOT let the cascade delete proof records; MUST NOT trust a client-supplied completion time.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Subtle carve-out where a mistake either leaks PII into the surviving record or removes accountability evidence; favor the strongest reasoning on the cascade-exclusion and fail-closed commit ordering. Mandatory human privacy/security review; keep the completion gate in lockstep with issue 048 and the chain shape with 012.
