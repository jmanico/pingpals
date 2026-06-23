# Requirement: Automated retention job with chain-preserving audit purge

## Metadata
- **ID**: REQ-PRIV-051
- **Title**: Storage-limitation retention job and tamper-evidence-preserving audit purge with separate accountability retention
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Compliance

## Requirement
- **Description**: The system MUST enforce storage limitation through a configurable retention policy with an automated job that deletes data past retention and logs the action (`PRIV-1.9`). Audit-log retention MUST preserve tamper-evidence and MUST NOT delete or rewrite individual audit entries in a way that breaks the append-only/hash chain (`SEC-8.4`): where audit entries are aged out, they MUST be removed only as sealed, independently verifiable segments, with the surviving chain re-anchored, and the purge MUST itself be recorded as a tamper-evident audit event. Security and DSR/accountability events (authentication, authorization denials, integration token use, consent changes, DSR actions, deletions) MUST be governed by a distinct accountability retention period — separate from, and not shorter than, operational-PII retention — sized to the accountability obligation. The purge MUST fail closed: if it cannot remove a segment while keeping the remaining chain verifiable, it MUST halt and alert rather than truncate or splice the chain.
- **Rationale**: GDPR Article 5(1)(e) storage limitation requires data not be kept longer than necessary, while Article 5(2) accountability requires security/DSR evidence be retained long enough to demonstrate compliance — two retention clocks that must not collide. Naive deletion of audit rows would break the tamper-evident chain and destroy both accountability and detectability. This is the data-of-record behind `PRIV-1.9` and `SEC-8.4`.
- **Design**: The retention job has no user-facing surface; any operator-facing report uses the gentle, non-PII operational voice (`NFR-1.3`, `DESIGN.md` §6 tone for any messaging).

## Scope
- **Applies To**: API (background job)
- **Components**: Privacy/DSR subsystem (retention job) + tamper-evident audit log (012); operates across all per-user-scoped PII stores and the audit store; coordinates with export-artifact deletion (047) and backup purge (048).
- **Actors**: Scheduled retention job (system principal, no ambient user trust); auditor (verifies surviving chain).
- **Data Classification**: Restricted/PII (operational data) and Restricted (audit log).

## Security Context
- **Defense Layer**: Architecture (segmented purge + re-anchoring) + Logging/audit integrity
- **Threat(s) Addressed**: Tamper-via-retention (deleting/rewriting audit entries to hide activity, CWE-778/CWE-117), premature deletion of accountability evidence, storage-limitation overrun. STRIDE: Tampering, Repudiation, Information Disclosure.
- **Trust Boundary**: Audit subsystem + persistence — the purge runs with segregated write access to audit storage (`SEC-8.5`) and re-anchors the surviving chain head in the separate anchor store.
- **Zero Trust Consideration**: The job verifies chain integrity before and after each segment purge; it never trusts that a delete "left the chain fine" — it re-verifies and halts on any break.

## Standards Alignment
- **OWASP ASVS**: V7.x (log retention/integrity), V8.x (data retention & disposal)
- **OWASP AISVS**: n/a (no AI component)
- **NIST SP 800-53**: AU-4/AU-11 (audit storage & retention), AU-9 (protection of audit information), SI-12 (retention/disposal)
- **NIST SP 800-207**: continuous verification of integrity state
- **Regulatory**: GDPR Arts. 5(1)(e) (storage limitation), 5(2) (accountability retention)
- **Other**: `PRIV-1.9`, `SEC-8.4`, `SEC-8.5`, `SEC-8.1`, `PRIV-1.16` (proof records survive)

## Acceptance Criteria
1. **AC-01 (verbatim `PRIV-1.9`)**: Given records whose retention has elapsed, when the retention job runs, then it deletes those records and logs the action.
2. **AC-02 (verbatim `SEC-8.4`)**: Given a retention purge runs over audit data, when it completes, then an integrity check confirms the remaining audit chain still verifies end to end, the purge is itself logged as a tamper-evident entry, and security/DSR events within the accountability period are retained even if past operational-PII retention.
3. **AC-03**: Given the accountability retention period, when configured, then it is distinct from and not shorter than operational-PII retention, and security/DSR event classes are governed by it.
4. **AC-04 (negative)**: Given the job cannot remove an audit segment while keeping the remaining chain verifiable, when it runs, then it halts and raises an alert (no truncate/splice of the chain — fail closed).
5. **AC-05 (negative)**: Given a security/DSR/accountability event still inside the accountability period, when the operational-PII retention clock elapses, then that event is NOT deleted.

## Failure Behavior
- **On Invalid Input**: A misconfigured retention policy (e.g. accountability shorter than operational) is rejected/refused at load; the job does not run with an unsafe policy.
- **On System Error**: Fail closed — if a segment cannot be sealed/re-anchored/verified, halt and alert rather than partially purge; never break the chain to make progress.
- **Alerting**: Any halted purge, detected chain break, missing anchor, or unsafe policy raises an operational + tamper alert.

## Test Strategy
- **Unit Tests**: Retention-eligibility computation per record class; accountability-vs-operational period separation; segment sealing + re-anchoring logic.
- **Integration Tests**: Age out operational PII while retaining in-period accountability events; purge an audit segment and verify the surviving chain re-verifies end to end (maps to TEST-1.4 retention expiry).
- **Security Tests**: Force a segment that cannot be removed without breaking verifiability and assert the job halts + alerts; tamper test confirms an out-of-order/removed historical entry is detected post-purge (`SEC-8.5`).
- **Compliance Tests**: Automated evidence that the purge logged its own tamper-evident event and that accountability-period events survived an operational-retention sweep.
- **Coverage Target**: ≥ 80% branch coverage of the retention + audit-purge module.

## Dependencies
- **Upstream**: 012 (tamper-evident audit log + chain verifier + anchor store), 010 (per-user-scoped persistence for operational PII), 011 (encryption — applies to retained/purged stores), 049 (proof-of-erasure records survive within accountability retention).
- **Downstream**: 047 (export-artifact deletion on retention), 048 (backup purge schedule aligns with this job), 053 (RoPA documents retention periods).
- **External**: None (cron/scheduler mechanism `TO BE DECIDED`; keep behind an interface).

## Implementation Notes
- **Constraints**: Two configurable clocks — operational-PII and accountability — with the invariant accountability ≥ operational for security/DSR classes. Audit purge operates on sealed segments only and re-anchors the head (`SEC-8.5`). Server-authoritative time for all logged actions (`SEC-8.3`). `Split recommendation:` if the audit-segment sealing/re-anchoring logic grows large, split it from the operational-PII sweep into its own issue.
- **Anti-Patterns**: MUST NOT delete or rewrite individual audit entries in place; MUST NOT truncate/splice the chain to make progress; MUST NOT let operational retention delete in-period accountability events; MUST NOT run under a policy where accountability < operational.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Tamper-evidence-preserving purge with two interacting retention clocks and fail-closed halting — favor the strongest reasoning on chain integrity and re-anchoring edge cases. Mandatory human security review; keep the segment/anchor shape in lockstep with issue 012.
