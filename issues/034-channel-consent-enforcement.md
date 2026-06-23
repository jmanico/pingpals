# Requirement: Per-channel consent enforcement — fail closed from the latest immutable record

## Metadata
- **ID**: REQ-ENG-034
- **Title**: Affirmative per-channel consent required for delivery; evaluated only from the latest immutable consent record; fails closed
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Critical
- **Classification**: Security (privacy/compliance: GDPR consent enforcement)

## Requirement
- **Description**: For each enabled notification channel the system MUST hold an affirmative, recorded consent before delivering any reminder on that channel; absence of consent MUST **fail closed** (no delivery on that channel). Per-channel delivery authorization MUST be evaluated **only from the latest immutable consent record** for that channel (sourced from the consent store, issue 045) and MUST fail closed if record integrity cannot be established. This consent gate MUST be enforced both at scheduler evaluation (issue 031, as a generation precondition) and again at delivery time (independent re-check), so a withdrawal between generation and delivery still suppresses the send.
- **Rationale**: GDPR requires explicit, granular, withdrawable consent per channel (`PRIV-1.2`); delivering on a channel without an active grant is unlawful processing. Evaluating only from the latest immutable record (`PRIV-1.15`) and failing closed on integrity failure (`FR-6.2`) prevents stale, edited, or unverifiable consent from authorizing delivery, and the dual-point check closes the generate-then-withdraw race.
- **Design**: Per `DESIGN.md` §6, consent and channel choices are presented clearly; a channel with no active consent is simply not offered/used, never a silent fallback.

## Scope
- **Applies To**: Both
- **Components**: Consent-evaluation service consumed by the scheduler (031) and the delivery worker; immutable consent store (045); audit log (012).
- **Actors**: Authenticated user (owner) grants/withdraws consent; scheduler and delivery worker are internal consumers.
- **Data Classification**: Restricted (consent records are Restricted; deliveries reference contact personal data).

## Security Context
- **Defense Layer**: Architecture (fail-closed consent gate at two enforcement points, latest-immutable-record evaluation)
- **Threat(s) Addressed**: Unlawful delivery without consent (GDPR Art. 6), stale/edited/backdated consent authorizing delivery (CWE-345), generate-then-withdraw race, integrity-unverifiable consent fail-open. STRIDE: Tampering, Repudiation, Information Disclosure.
- **Trust Boundary**: Internal east-west — both the scheduler and the delivery worker independently re-evaluate consent; neither trusts the other's prior decision (defense in depth, SECURITY §3).
- **Zero Trust Consideration**: Consent is re-derived from the latest immutable record at each enforcement point; an indeterminate or integrity-failed record resolves to deny (no delivery).

## Standards Alignment
- **OWASP ASVS**: V7 (business logic), V8 (data protection), V9 (integrity)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: AC-3, AU-10 (non-repudiation), SI-7 (integrity)
- **NIST SP 800-207**: indeterminate decision resolves to deny; per-decision evaluation inside the boundary
- **Regulatory**: GDPR Art. 6 (lawfulness), Art. 7 (conditions for consent), Art. 5(2) accountability
- **Other**: `FR-6.2`, `PRIV-1.2`, `PRIV-1.15`, ARCH Dependency Rule 3

## Acceptance Criteria
1. **AC-01 (verbatim `FR-6.2`)**: Given a channel with no affirmative recorded consent, when delivery on that channel is attempted, then it fails closed (no delivery on that channel).
2. **AC-02 (verbatim `PRIV-1.15`)**: When per-channel delivery authorization is evaluated, then it is derived solely from the latest immutable consent record, and a missing or integrity-failed record yields no delivery on that channel.
3. **AC-03 (verbatim `PRIV-1.2`)**: Given any delivered reminder, when the consent history is inspected, then it shows an active grant for the chosen channel with no intervening withdrawal at the delivery timestamp.
4. **AC-04**: Given consent is withdrawn after generation but before delivery, when delivery runs, then the delivery-time re-check fails closed and no send occurs.
5. **AC-05 (negative)**: Given a consent record whose integrity cannot be established (e.g., chain/hash verification fails), when evaluated, then no delivery occurs on that channel and the denial is audited (`SEC-8.1`).
6. **AC-06 (negative)**: Given consent state for a channel cannot be determined unambiguously, when evaluated, then delivery on that channel fails closed (`PRIV-1.2`).

## Failure Behavior
- **On Invalid Input**: A consent query for a non-owned channel/user resolves to deny (not-found/forbidden); no delivery.
- **On System Error**: Fail closed — consent-store unavailability, integrity failure, or indeterminate state yields no delivery on that channel (`SEC-2.3`, `NFR-1.6`); never degrade to a weaker path.
- **Alerting**: A consent integrity-verification failure MUST raise a security alert and be audited.

## Test Strategy
- **Unit Tests**: Latest-immutable-record selection; absent-consent fail-closed; integrity-failure fail-closed; indeterminate-state fail-closed.
- **Integration Tests**: Grant→deliver (allowed); withdraw-between-generation-and-delivery → delivery-time re-check suppresses send; consent fail-closed delivery (TEST-1.4).
- **Security Tests**: Tampered/backdated consent record rejected; cross-user consent denied; denial audited.
- **Compliance Tests**: For each delivered reminder, evidence of an active grant with no intervening withdrawal at the delivery timestamp (`PRIV-1.2`); denials present in the audit log.
- **Coverage Target**: ≥ 80% branch coverage of the consent-evaluation module (aim higher — it is compliance-critical).

## Dependencies
- **Upstream**: 045 (immutable consent store), 012 (audit log + integrity verification), 031 (scheduler enforces consent as a generation precondition), 010 (per-user scoping), 014 (authorization).
- **Downstream**: Delivery worker (later issue) re-checks consent at send time; 044 (notification preferences reference enabled channels).
- **External**: Consent store backing engine (`TO BE DECIDED`) — keep behind the immutable-consent interface (issue 045), default to fail-closed/deny.

## Implementation Notes
- **Constraints**: Consent evaluation is a pure function over the latest immutable record from issue 045; it is invoked at **both** scheduler-evaluation time and delivery time (defense in depth). No mass-assignment of consent through preferences/contact writes (`PRIV-1.15`, enforced in 024/045). Integrity of the consent record is checked via the audit/hash-chain (issue 012).
- **Anti-Patterns**: MUST NOT cache a stale "consent present" decision past a possible withdrawal; MUST NOT evaluate consent from anything but the latest immutable record; MUST NOT fail open when the record's integrity is unverifiable; MUST NOT enforce consent at only one of the two points.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** Consent fail-closed at two enforcement points, against an immutable/integrity-checked record, with a generate-then-withdraw race to close, is directly GDPR-load-bearing; a fail-open slip is unlawful processing. Mandatory human privacy + security review before merge.
