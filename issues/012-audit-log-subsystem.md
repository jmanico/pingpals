# Requirement: Tamper-evident audit log subsystem

## Metadata
- **ID**: REQ-BE-012
- **Title**: Append-only / hash-chained audit log with externally-anchored, independently-verified integrity
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Critical
- **Classification**: Security

## Requirement
- **Description**: The backend MUST produce a tamper-evident audit log (append-only or hash-chained) covering, at minimum: authentication events, authorization denials, integration token use, consent grant and withdrawal, rectification of contact personal data, DSR actions, and all deletions. Each entry MUST record the acting principal, the action, the affected object identity, and a server-authoritative timestamp (client-supplied time MUST NOT be trusted; an unavailable/unverifiable time source MUST fail closed — the record is rejected, not written with untrusted time). Where the user may legitimately assert an event time (e.g. a backdated last-contact log), the user-asserted event time and the immutable server record time MUST be stored as DISTINCT fields, and the record time is the basis for tamper-evidence. The audit write MUST share the same commit as the mutation it records: if the audit entry cannot be written, the mutation MUST fail closed and not be applied. The chain head MUST be anchored in a store separate from and not writable by the audit log's own write path; the system MUST periodically and independently verify the chain end to end, segregate write access to audit storage from the application's normal data path, and alert on any break, gap, missing anchor, or out-of-order entry. Retention MUST preserve tamper-evidence (age out only as sealed, independently verifiable segments with the surviving chain re-anchored) and MUST NOT delete/rewrite individual entries in a way that breaks the chain.
- **Rationale**: Anchored in `SEC-8.1`–`SEC-8.5` and `SEC-8.3`. A merely structural hash chain is defeated by an actor who rewrites records and recomputes downstream hashes; an external anchor plus active independent verification detects that. Same-commit audit writes give GDPR Art. 5(2) accountability and ensure no consent/DSR/deletion mutation is applied without a surviving record (supports `PRIV-1.16` proof-of-erasure).
- **Design**: No user-facing surface; supports the privacy and accountability guarantees the product promises.

## Scope
- **Applies To**: API
- **Components**: Flask API service — audit subsystem (append-only/hash-chained writer, external anchor store adapter, segregated audit-storage access, periodic verifier job, alerting hook). Consumed by auth, authz, integration adapters, consent/DSR, and persistence on every covered mutation.
- **Actors**: All acting principals (user, Scheduler, Delivery worker, adapters) are recorded; the verifier runs as a privileged background job with segregated access.
- **Data Classification**: Restricted (audit entries reference object identities); entries MUST exclude secrets, tokens, and message content (`SEC-8.2`). Per §3.

## Security Context
- **Defense Layer**: Architecture + Logging/Accountability (tamper-evident, independently verified).
- **Threat(s) Addressed**: Audit tampering / repudiation (CWE-117 log neutralization, CWE-778 insufficient logging), backdating/forged timestamps (CWE-639/CWE-294), silent record rewrite with recomputed hashes (chain-forgery), audit-write skipped on failure leaving an unrecorded mutation. STRIDE: Repudiation, Tampering, Information Disclosure.
- **Trust Boundary**: The audit storage and its anchor — write access is segregated from the application's normal data path, and the anchor lives outside the audit write path so the log cannot self-certify a forgery.
- **Zero Trust Consideration**: The audit log is not trusted to be intact on the basis of its own contents; integrity is independently and periodically verified against an external anchor, and any unverifiable/broken/unanchored chain is treated as a tamper event, never silently accepted (fail closed).

## Standards Alignment
- **OWASP ASVS**: V7.1 (log content), V7.2 (log protection), V7.3 (log integrity)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: AU-2 (audit events), AU-9 (protection of audit information), AU-10 (non-repudiation), AU-8 (time stamps), AU-11 (retention)
- **NIST SP 800-207**: continuous, independent verification rather than implicit trust
- **Regulatory**: GDPR Art. 5(2) accountability, Art. 30 (records of processing — supports), Art. 33/34 (breach evidence)
- **Other**: SECURITY.md §6; `SEC-8.1`–`SEC-8.5`, `SEC-8.3`, `PRIV-1.2`, `PRIV-1.16`

## Acceptance Criteria
1. **AC-01 (verbatim `SEC-8.1`)**: Given a channel consent is granted and then withdrawn, when audited, then two distinct, ordered, attributable audit entries are produced; and given a mutation whose audit write is forced to fail, then no change is persisted.
2. **AC-02 (verbatim `SEC-8.3`)**: Given a contact event or consent change submitted with a past or future user-asserted time, when recorded, then the true server time is the immutable record time, the asserted time is preserved in a separate field; and given the authoritative time source is unavailable, then the record is rejected (not written with untrusted time).
3. **AC-03 (verbatim `SEC-8.5`)**: Given a test that mutates, reorders, or removes a historical entry (including tail truncation), when the next integrity check runs, then it fails and emits an alert.
4. **AC-04 (verbatim `SEC-8.4`)**: Given a retention purge ages out audit entries, when it completes, then an integrity check confirms the remaining chain verifies end to end, the purge is itself logged as a tamper-evident entry, and security/DSR events within the accountability period are retained even if past operational-PII retention.
5. **AC-05 (negative)**: Given an entry whose timestamp is client-supplied, when written, then the client time is not used as the record time (server-authoritative time only, `SEC-8.3`).
6. **AC-06 (negative)**: Given an attempt to write to audit storage via the application's normal data path, when access is checked, then it is denied — write access is segregated (`SEC-8.5`).

## Failure Behavior
- **On Invalid Input**: An entry lacking a server-authoritative timestamp or required principal/object identity is rejected; the accompanying mutation fails closed.
- **On System Error**: Fail closed — if the audit entry cannot be committed in the mutation's transaction, the mutation is not applied; if the anchor is unreachable, integrity is treated as unverified and surfaced.
- **Alerting**: Any detected break, gap, missing anchor, or out-of-order entry raises a security alert; audit-storage write failures and anchor unavailability alert immediately.

## Test Strategy
- **Unit Tests**: Hash-chain link/verify; server-time assignment and asserted-vs-record-time field separation; same-commit audit+mutation (rollback on audit failure).
- **Integration Tests**: Consent grant→withdraw produces two ordered entries; forced audit-write failure rolls back the mutation; retention purge re-anchors and stays verifiable.
- **Security Tests**: Tamper/reorder/truncate corpus triggers verification failure + alert; external-anchor forgery test (rewrite + recompute downstream hashes still detected); access-segregation probe from the normal data path.
- **Compliance Tests**: Evidence that all `SEC-8.1` event classes are logged with principal/object/server-time; accountability-retention separation from operational-PII retention.
- **Coverage Target**: ≥ 80% branch coverage of the audit writer and verifier.

## Dependencies
- **Upstream**: 007 (Flask skeleton), 010 (persistence — `AuditLogEntry` table and same-commit transaction), 069 (DECISION: database engine for the transactional commit guarantee).
- **Downstream**: 011 (decrypt/denial events), 014 (authz denials), 015/016 (denials), consent/DSR/erasure issues (`PRIV-1.2`, `PRIV-1.16`), delivery audit (SECURITY.md §6 delivery-attempt events), retention job (`PRIV-1.9`/`SEC-8.4`).
- **External**: External anchor store (separate from audit write path; concrete store `TO BE DECIDED`, behind an interface defaulting to treat-as-unverified when unreachable).

## Implementation Notes
- **Constraints**: The audit write must be in the same transaction/commit as its mutation (engine-dependent — DECISION 069; keep behind the persistence interface). The anchor store must not be writable by the audit write path. Verifier runs periodically and on demand. Accountability-retention period is distinct from and not shorter than operational-PII retention.
- **Anti-Patterns**: MUST NOT trust client-supplied time as the record time; MUST NOT write the mutation if the audit entry fails (no best-effort logging); MUST NOT let the audit log self-certify (anchor must be external); MUST NOT delete/rewrite individual entries breaking the chain; MUST NOT include secrets/tokens/message content (`SEC-8.2`); MUST NOT splice or truncate the chain during retention — halt and alert instead.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Tamper-evidence with external anchoring, same-commit semantics, and fail-closed time handling has subtle correctness requirements where a small mistake silently destroys non-repudiation. Favor the model with stronger reasoning about cryptographic-chain and transactional invariants. Mandatory human security review of the chaining, anchoring, and verification logic before merge.
