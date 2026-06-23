# Requirement: GDPR governance documentation (RoPA, DPIA, LIA, DPAs, breach process)

## Metadata
- **ID**: REQ-PRIV-053
- **Title**: Record of Processing Activities, DPIA, Legitimate Interests Assessment, DPAs/transfer mechanism, and breach-notification process
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Compliance

## Requirement
- **Description**: The controller MUST produce and maintain the following GDPR governance artifacts as version-controlled markdown deliverables: (a) a Record of Processing Activities per Article 30 (`PRIV-1.10`); (b) a Data Protection Impact Assessment per Article 35, completed before production launch, given systematic processing that includes non-user data subjects (`PRIV-1.11`); (c) a documented lawful basis with a Legitimate Interests Assessment for contact personal data under Article 6(1)(f), recording that account data is processed under contract per Article 6(1)(b) (`PRIV-1.1`); (d) Data Processing Agreements covering all processors (email, SMS, contacts, calendar, hosting) and a valid cross-border transfer mechanism (for example Standard Contractual Clauses) where applicable (`PRIV-1.12`); and (e) a personal-data-breach assessment and 72-hour supervisory-authority notification process per Articles 33/34 (`PRIV-1.14`). These artifacts MUST receive qualified data-protection-advisor sign-off before production launch (REQUIREMENTS §14 open question).
- **Rationale**: These are not optional: Articles 30/35 mandate the records and the DPIA, Article 6 requires a documented lawful basis, Article 28 requires DPAs with processors, Chapter V governs transfers, and Articles 33/34 set the breach clock. Because Pingpals processes non-user data subjects' personal data, the DPIA and advisor review are prerequisites to launch. This is the documentation-of-record behind `PRIV-1.1`, `PRIV-1.10`, `PRIV-1.11`, `PRIV-1.12`, and `PRIV-1.14`.
- **Design**: These are documents, not UI. Any user-facing privacy notice derived from them follows `DESIGN.md` §6 tone; the artifacts themselves are plain, auditable markdown.

## Scope
- **Applies To**: Both (governance documentation describing the whole system)
- **Components**: Privacy/DSR subsystem governance — documentation set; references the consent store (045), DSR endpoints (050), erasure/proof (048/049), retention (051), privacy-by-default and Art. 9 notes risk (052).
- **Actors**: Controller / privacy lead (author); qualified data-protection advisor (mandatory sign-off gate); processors (parties to DPAs).
- **Data Classification**: Internal (the documents describe processing; they MUST NOT embed Restricted contact PII — only categories and flows).

## Security Context
- **Defense Layer**: Architecture (governance / accountability documentation)
- **Threat(s) Addressed**: Unlawful processing without a documented basis, undisclosed high-risk processing (no DPIA), uncovered processors / unlawful cross-border transfer, missed breach-notification deadline (regulatory and data-subject harm). STRIDE: Repudiation (accountability), Information Disclosure (transfers/breach).
- **Trust Boundary**: Organizational/legal boundary — these artifacts define the lawful basis and processor obligations under which the technical trust boundaries operate; they are the accountability layer above the code.
- **Zero Trust Consideration**: No processing is assumed lawful by default; each processing activity in the RoPA must name a basis, and each processor must be covered by a DPA before data flows — absent documentation, the activity is treated as not authorized (fail closed at the governance layer).

## Standards Alignment
- **OWASP ASVS**: n/a (governance documentation, not code)
- **OWASP AISVS**: n/a (no AI component; if added, REQUIREMENTS §12 governance applies)
- **NIST SP 800-53**: PM family / privacy program controls (RoPA, PIA/DPIA analogues), IR-6 (incident reporting), SA-9 (external service agreements / DPAs)
- **NIST SP 800-207**: n/a (organizational layer)
- **Regulatory**: GDPR Arts. 6(1)(b)/(f) (basis + LIA), 28 (DPAs), 30 (RoPA), 33/34 (breach notification), 35 (DPIA), Chapter V / Art. 46 (transfers, SCCs)
- **Other**: `PRIV-1.1`, `PRIV-1.10`, `PRIV-1.11`, `PRIV-1.12`, `PRIV-1.14`, REQUIREMENTS §14, DECISION 073 (hosting/region/residency)

## Acceptance Criteria
1. **AC-01**: Given the governance set, when reviewed, then a Record of Processing Activities (Art. 30) exists enumerating each processing activity, its purpose, data categories, recipients, transfers, and retention (`PRIV-1.10`).
2. **AC-02**: Given pre-launch readiness, when assessed, then a completed DPIA (Art. 35) exists addressing the non-user data-subject processing and the free-text-notes Article 9 residual risk from issue 052 (`PRIV-1.11`, `PRIV-1.18`).
3. **AC-03**: Given the lawful-basis artifact, when reviewed, then it documents legitimate interests (Art. 6(1)(f)) with a Legitimate Interests Assessment for contact data and contract (Art. 6(1)(b)) for account data (`PRIV-1.1`).
4. **AC-04**: Given each processor (email, SMS, contacts, calendar, hosting), when checked, then a DPA covers it and a valid cross-border transfer mechanism (e.g. SCCs) is in place where applicable, consistent with the hosting region from DECISION 073 (`PRIV-1.12`).
5. **AC-05**: Given a personal-data-breach scenario, when the documented process runs, then it defines assessment, 72-hour supervisory-authority notification (Art. 33), and data-subject notification where Art. 34 applies (`PRIV-1.14`).
6. **AC-06 (negative / human gate)**: Given production launch is proposed, when the governance set lacks qualified data-protection-advisor sign-off, then launch is blocked (the advisor review is a mandatory human gate, REQUIREMENTS §14).

## Failure Behavior
- **On Invalid Input**: A processing activity with no documented lawful basis, or a processor with no DPA, is treated as not authorized — flagged and blocked at the governance gate rather than proceeding.
- **On System Error**: Fail closed (organizational) — absent the DPIA or advisor sign-off, production launch does not proceed; absent a transfer mechanism, the affected processing/region is not used.
- **Alerting**: A processing change with no RoPA entry, an uncovered processor, or a breach event triggers the documented review/notification workflow.

## Test Strategy
- **Unit Tests**: n/a (documentation deliverables; not executable).
- **Integration Tests**: Traceability check that each technical issue (045–052) is reflected in the RoPA/DPIA (e.g. consent model, erasure cascade, retention periods, Art. 9 notes risk).
- **Security Tests**: n/a directly; the DPIA references the SECURITY.md controls and verification evidence.
- **Compliance Tests**: Automated/manual evidence collection — presence of RoPA, DPIA, LIA, each processor DPA, transfer mechanism, breach process, and the advisor sign-off record; CI/doc lint can assert the files exist and are non-empty.
- **Coverage Target**: n/a (documentation); completeness checklist MUST cover every Art. 30 field and every processor.

## Dependencies
- **Upstream**: 045 (consent model — RoPA/DPIA evidence), 048/049 (erasure + proof — accountability), 050 (DSR process — RoPA), 051 (retention periods — RoPA), 052 (privacy-by-default + Art. 9 notes residual risk — DPIA/LIA).
- **Downstream**: Production launch gate (all `PRIV` issues feed launch readiness); DECISION 073 (hosting/region/residency) bounds the transfer-mechanism section.
- **External**: Processor counterparties (transactional email, Google People, hosting) for DPAs; a qualified data-protection advisor for the mandatory sign-off.

## Implementation Notes
- **Constraints**: Artifacts are version-controlled markdown referencing the technical issues as evidence; they MUST NOT embed Restricted contact PII. The hosting region / data residency (DECISION 073) determines whether SCCs or another transfer mechanism is required — do not assume a region; surface the open decision. The qualified-advisor sign-off and the DPIA-before-launch are human gates, not code.
- **Anti-Patterns**: MUST NOT launch to production without the DPIA and advisor sign-off; MUST NOT process via a processor lacking a DPA; MUST NOT assume the household-exemption (Art. 2(2)(c)) shields the controller (REQUIREMENTS §14); MUST NOT embed contact PII in the governance documents.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Structured, comprehensive documentation drafting against an enumerated regulatory checklist, suited to broad systematic coverage. **Open Question / human gate:** the lawful-basis determination, DPIA conclusions, and transfer mechanism require qualified data-protection-advisor review before launch — AI drafts, a human advisor signs off; this gate MUST NOT be auto-resolved.
