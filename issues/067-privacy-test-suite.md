# Requirement: Privacy test suite (erasure cascade, export completeness, consent fail-closed, retention expiry)

## Metadata
- **ID**: REQ-TEST-067
- **Title**: Mandatory privacy/GDPR test cases for the TEST-1.4 control set
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Privacy

## Requirement
- **Description**: The test suite MUST include privacy test cases that cover, at minimum: erasure cascade (`PRIV-1.6`), data-export completeness (`PRIV-1.5`), consent fail-closed delivery (`FR-6.2`), and retention expiry (`PRIV-1.9`). Each MUST have explicit positive and negative cases, and these cases MUST run in CI as part of the blocking gate (issue 003) on the harness (issue 065).
- **Rationale**: `TEST-1.4` enumerates exactly these four privacy control areas as mandatory test coverage. Because Pingpals processes personal data of third-party data subjects (contacts who are not users), GDPR obligations (Arts. 5, 6, 15–21) are load-bearing; these tests are the standing evidence that erasure, export, consent, and retention controls remain enforced.
- **Design**: Per `DESIGN.md`, no end-user UI; the suite produces developer/CI evidence. Tests MUST use synthetic personal data and MUST NOT print contact PII in assertion output (`SEC-8.2`).

## Scope
- **Applies To**: Both
- **Components**: Erasure cascade (048), proof-of-erasure (049), data export (046) and its access control (047), consent records store (045) and channel-consent enforcement (034), delivery worker (035), retention job (051).
- **Actors**: An authenticated owning user exercising DSRs; a second user (for export/erasure scoping); the scheduler/delivery worker (for consent fail-closed).
- **Data Classification**: Restricted (contact PII, consent records — synthetic in tests).

## Security Context
- **Defense Layer**: Architecture / Verification (asserts privacy-by-design controls remain in force).
- **Threat(s) Addressed**: Incomplete erasure leaving orphaned PII (GDPR Art. 17 non-compliance), under-complete export (Art. 15/20), delivery on a channel without valid consent (unlawful processing, Art. 6), data retained past its limit (Art. 5(1)(e)). STRIDE: Information Disclosure, Repudiation.
- **Trust Boundary**: Exercises the DSR/privacy subsystem and the scheduler→delivery consent gate; verifies each fails closed.
- **Zero Trust Consideration**: Consent is evaluated per delivery from the latest immutable record; tests assert that an absent/indeterminate consent state yields no delivery rather than a default-allow.

## Standards Alignment
- **OWASP ASVS**: V8.x (data protection / privacy)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: AU-11 (audit retention), SI-12 (information handling/retention), AC-3 (access enforcement for export)
- **NIST SP 800-207**: deny-by-default for consent decisions
- **Regulatory**: GDPR Arts. 5(1)(e), 6, 15, 17, 20, 21 — erasure, export, consent, retention
- **Other**: `TEST-1.4`, `PRIV-1.6`, `PRIV-1.5`, `FR-6.2`, `PRIV-1.9`, `PRIV-1.16`, `PRIV-1.17`

## Acceptance Criteria
[Each criterion MUST be independently testable.]

1. **AC-01 (erasure cascade)**: Given a contact with reminders, outreach history, derived data, and tokens, when erasure runs, then a post-deletion query returns no personal data for the subject in primary storage. *(verbatim `PRIV-1.6`: an erasure test confirms no personal data for the subject remains in primary storage after completion.)*
2. **AC-02 (export completeness)**: Given a user's data, when exported, then the machine-readable artifact round-trips all contact, category, cadence, consent, and history records. *(verbatim `PRIV-1.5`: an exported file round-trips all contact, category, cadence, consent, and history records.)*
3. **AC-03 (consent fail-closed)**: Given a channel with no active consent (or an indeterminate consent state), when a reminder is due on that channel, then no delivery occurs. *(verbatim `FR-6.2`: absence of consent MUST fail closed — no delivery on that channel; and `PRIV-1.2`: where consent cannot be determined unambiguously, delivery fails closed.)*
4. **AC-04 (retention expiry)**: Given records whose retention has elapsed, when the retention job runs, then those records are deleted and the action is logged. *(verbatim `PRIV-1.9`: the retention job deletes records whose retention has elapsed and logs the action.)*
5. **AC-05 (negative — proof survives erasure)**: Given an erasure, when complete, then a PII-free, tamper-evident proof-of-erasure record for the subject remains retrievable and its hash chain validates. *(verbatim `PRIV-1.16`: after an erasure, a post-deletion query returns no contact personal data yet a PII-free, tamper-evident proof-of-erasure record remains and its hash chain validates.)*
6. **AC-06 (negative — consent grant/withdraw ordering)**: Given a consent grant then withdrawal, when delivery is evaluated at the post-withdrawal timestamp, then no delivery is authorized (latest immutable record governs).
7. **AC-07 (negative — coverage)**: Given the suite, when run in CI, then absence of any of the four mandated case groups fails the build.

## Failure Behavior
- **On Invalid Input**: A failing privacy assertion fails the CI gate and blocks merge; the report names the violated control without printing PII.
- **On System Error**: Fail closed — an errored or skipped privacy test counts as a failure.
- **Alerting**: A regression in any TEST-1.4 case raises a privacy-gate failure on the PR.

## Test Strategy
- **Unit Tests**: Consent-state resolver (latest immutable record, fail-closed on indeterminate); retention-eligibility predicate; export serializer completeness against the entity set.
- **Integration Tests**: End-to-end erasure across all stores then a residual-PII sweep; export round-trip parsed back and diffed against seeded data; scheduler/delivery run with consent absent/withdrawn asserting zero deliveries; retention job over time-aged fixtures.
- **Security Tests**: Attempt cross-user export/erasure (must be denied — ties to 047 and SEC-2.2); confirm proof-of-erasure excludes PII and survives the cascade.
- **Compliance Tests**: CI evidence that all four TEST-1.4 groups executed and passed; export/erasure produce audit entries (`SEC-8.1`).
- **Coverage Target**: ≥80% branch coverage of privacy-test helpers; the residual-PII sweep MUST cover all stores holding contact data.

## Dependencies
- **Upstream**: 065 (harness/coverage gate), 045 (consent store), 046 (export), 047 (export access control), 048 (erasure cascade), 049 (proof-of-erasure), 051 (retention job), 034 (channel-consent enforcement), 035 (delivery worker), 012 (audit log).
- **Downstream**: 003 (CI gate); GDPR compliance evidence for the DPIA (053) draws on these passing tests.
- **External**: None (synthetic fixtures only).

## Implementation Notes
- **Constraints**: The residual-PII sweep MUST enumerate every store/table holding contact data from the schema (issue 010 / decision 069), so a new PII-bearing table is automatically in scope. Retention tests MUST control the clock deterministically (injectable time source per `SEC-8.3`).
- **Anti-Patterns**: MUST NOT assert erasure only on the primary contact row while leaving reminders/history/tokens unchecked; MUST NOT default consent to allow when state is indeterminate; MUST NOT print contact PII in failure messages; MUST NOT delete the proof-of-erasure record in the cascade.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** GDPR-correct test design (complete cascade enumeration, fail-closed consent edge cases, proof-of-action survival) requires careful reasoning about regulatory completeness and adversarial gaps; the stronger model reduces the risk of a superficially-green but incomplete suite. Mandatory human privacy/legal review of the cascade enumeration before merge.
