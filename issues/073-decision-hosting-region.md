# Requirement: DECISION — hosting cloud / region / data residency

## Metadata
- **ID**: REQ-DEC-073
- **Title**: Decide and document the hosting cloud, region, and data residency for cross-border transfer
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Compliance
- **Decision**: **STILL DEFERRED — `TO BE DECIDED`.** Intentionally deferred cloud-agnostic; the deployment stays cloud-portable behind interfaces with no region committed. This deferral **BLOCKS finalizing processor DPAs (`PRIV-1.12`, issue 053)** and remains an open question pending DPO/legal input.

## Requirement
- **Description**: The team MUST decide and document the hosting cloud, region, and data-residency posture, including the cross-border transfer mechanism where applicable (`ARCHITECTURE.md` `TO BE DECIDED`; REQUIREMENTS.md §14 open question; `PRIV-1.12`). The decision MUST be recorded with rationale against the criteria below, satisfy every listed constraint, and be signed off by a human before processor Data Processing Agreements (DPAs) are finalized (issue 053). This issue produces NO implementation code and MUST NOT silently resolve the choice (`CLAUDE.md`).
- **Rationale**: All processors MUST be covered by a DPA and cross-border transfers MUST rely on a valid transfer mechanism (e.g. Standard Contractual Clauses) where applicable (`PRIV-1.12`). The hosting region bounds the transfer obligations and adequacy analysis, which REQUIREMENTS.md §14 flags as an open decision affecting the whole GDPR posture.
- **Design**: Not a UI feature; `DESIGN.md` does not apply.

## Scope
- **Applies To**: Both (the entire deployment runs in the chosen region)
- **Components**: Hosting/deployment, persistence (010 / decision 069), KMS (decision 072), processor DPAs and RoPA/DPIA docs (053).
- **Actors**: Architects, DPO/legal, human approver; no runtime actor.
- **Data Classification**: Restricted (contact PII of third-party data subjects, tokens, consent — all reside in the chosen region).

## Security Context
- **Defense Layer**: Architecture / Compliance.
- **Threat(s) Addressed**: Unlawful cross-border transfer without a valid mechanism (GDPR Chapter V non-compliance), processor with no DPA, data residency violating commitments. STRIDE: Information Disclosure (jurisdictional exposure), Repudiation (accountability gaps).
- **Trust Boundary**: The jurisdictional/legal boundary around stored personal data; the region choice defines which legal regime governs the data.
- **Zero Trust Consideration**: Transfer mechanisms and processor agreements are verified explicitly rather than assumed; a processor without a confirmed DPA/transfer basis is not used (fail closed on engaging an uncovered processor).

## Standards Alignment
- **OWASP ASVS**: V1.x (architecture/governance)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SA-9 (external system services), PL-2 (system plan), AC-20 (use of external systems)
- **NIST SP 800-207**: n/a
- **Regulatory**: GDPR Art. 28 (processors/DPA), Arts. 44–49 (international transfers / SCCs / adequacy), Art. 30 (RoPA), Art. 35 (DPIA)
- **Other**: `PRIV-1.12`, REQUIREMENTS.md §14 open question

## Evaluation Criteria (constraints any choice MUST satisfy)
1. **Cross-border transfer mechanism** — for any data leaving the primary jurisdiction, a valid mechanism (e.g. SCCs) or adequacy decision exists (`PRIV-1.12`, GDPR Arts. 44–49).
2. **GDPR adequacy / residency** — the region's legal regime is compatible with processing third-party data-subject PII under the documented lawful basis (`PRIV-1.1`).
3. **Processor DPAs** — all processors (hosting, DB, KMS, email, push) in the chosen region are coverable by a DPA (`PRIV-1.12`, GDPR Art. 28).
4. **Portability** — consistent with the cloud-portable Docker packaging; the region/cloud choice does not force a single proprietary lock-in for MVP (ARCH "many clouds").
5. **Co-location of stores** — database (069), KMS (072), queue (070), and backups can reside in or transfer lawfully relative to the chosen region.
6. **Breach-notification reachability** — supports the 72-hour breach assessment/notification obligation to the relevant supervisory authority (`PRIV-1.14`).
7. **Backup residency** — backups/snapshots of Restricted data stay within the residency/transfer posture (`SEC-5.6`, `PRIV-1.6`).

## Candidate Options (evaluate, do NOT pick here)
- A primary EU/EEA region hosting (minimize cross-border transfer for EU data subjects).
- A non-EU region with SCCs / adequacy as the transfer basis (evaluate the transfer-mechanism burden).
- Multi-region with pinned data residency per user/region (evaluate operational complexity vs. compliance benefit).

> Each option MUST be scored against all seven criteria with rationale, in consultation with a qualified data protection advisor (§14). This issue does not select one.

## Acceptance Criteria
1. **AC-01**: Given the candidate options, when evaluated (with DPO/legal input), then each is scored against all seven criteria with documented rationale.
2. **AC-02**: Given the evaluation, when a choice is recommended, then it is recorded in `ARCHITECTURE.md` (replacing the `TO BE DECIDED`) and REQUIREMENTS.md §14 is updated, with rationale and explicit human sign-off.
3. **AC-03 (negative)**: Given any region/processor combination lacking a valid transfer mechanism or DPA coverage, when evaluated, then it is rejected and the reason recorded.
4. **AC-04 (negative — no silent resolution)**: Given this issue, when worked, then no region is committed and processor DPAs (053) are not finalized before human sign-off; until then deployment targets stay undecided and dependents are blocked.

## Failure Behavior
- **On Invalid Input**: n/a (decision artifact).
- **On System Error**: Until resolved, the processor-DPA work in 053 stays blocked, and decisions 069/070/071/072 that depend on regional availability remain partially constrained.
- **Alerting**: Flag 053 (and region-dependent infra decisions) as decision-blocked on the board while this is open.

## Test Strategy
- **Unit Tests**: n/a (no code). Provide a decision matrix and a transfer-mechanism mapping artifact.
- **Integration Tests**: n/a.
- **Security Tests**: n/a (governance decision).
- **Compliance Tests**: Confirm the chosen region/processors have executed DPAs and a documented transfer basis before launch (feeds DPIA in 053); confirm breach-notification path to the supervisory authority.
- **Coverage Target**: n/a (decision issue).

## Dependencies
- **Upstream**: 053 (RoPA/DPIA/LIA context), REQUIREMENTS.md §14 open questions; requires DPO/legal review.
- **Downstream**: **Blocks 053** (processor DPAs finalization); constrains regional availability for decisions 069 (DB), 070 (queue), 071 (push), 072 (KMS).
- **External**: Cloud provider region catalog; legal/DPO advisory; processor DPA templates / SCCs.

## Implementation Notes
- **Constraints**: Decision only — no code. Requires qualified data-protection-advisor review per §14 before sign-off. Keep cloud-portable so the choice does not foreclose later migration.
- **Anti-Patterns**: MUST NOT deploy to a region implicitly; MUST NOT engage a processor without a DPA and transfer basis; MUST NOT split stores across regions without a residency/transfer analysis.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Region/residency trade-off analysis over cloud-provider geographies and standard transfer mechanisms is a breadth-of-knowledge evaluation and documentation task; no code is produced. The model MUST NOT resolve the choice — it prepares the scored matrix and transfer-mechanism mapping for human DPO/legal sign-off.
