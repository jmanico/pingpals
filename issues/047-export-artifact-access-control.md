# Requirement: Access control, expiry, and retention for the data-export artifact

## Metadata
- **ID**: REQ-PRIV-047
- **Title**: Owner-only, expiring, single-use access control and bounded retention for export artifacts
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Security

## Requirement
- **Description**: The data export artifact (`PRIV-1.5`, issue 046) is Restricted data and MUST be access-controlled to the requesting authenticated user only. Any download link MUST require the owner's authenticated session **or** a short-lived, single-use, unguessable token; MUST expire; and MUST NOT be a long-lived, unauthenticated, or enumerable URL. Access MUST fail closed: an unauthenticated, expired, already-used, or non-owner request MUST be denied. The artifact MUST be deleted on a bounded retention schedule (`PRIV-1.9`) and on the requesting user's erasure (`PRIV-1.6`). Export generation and download are DSR actions and MUST therefore be rate-limited (`SEC-6.1`, 013) and audited (`SEC-8.1`, 012).
- **Rationale**: An export aggregates all of a user's Restricted data into one downloadable object — the highest-value single target in the system. A guessable or long-lived unauthenticated link would convert the access right into a data-breach vector. This control hardens the artifact produced by issue 046 and is the data-of-record behind `PRIV-1.17`.
- **Design**: Per `DESIGN.md` §6/§7, the "download your export" affordance appears only within the owner's authenticated session; an expired or used link shows a gentle, non-blaming message and offers re-generation rather than leaking why access failed.

## Scope
- **Applies To**: Both
- **Components**: Privacy/DSR subsystem — export download endpoint + token issuance/validation; artifact retention job; consumed by the web client download affordance.
- **Actors**: Authenticated user (owner) only; all other principals (unauthenticated, other users) are denied.
- **Data Classification**: Restricted/PII — the export artifact and any access token are Restricted.

## Security Context
- **Defense Layer**: Architecture (access control + token lifecycle) + Strict API
- **Threat(s) Addressed**: Broken object-level authorization / IDOR on the artifact (CWE-639, OWASP API1:2023), insecure direct object reference via enumerable URL (CWE-200), replay of a download link (CWE-294), data retention overrun. STRIDE: Information Disclosure, Elevation of Privilege, Tampering.
- **Trust Boundary**: API service — the download endpoint is the gate between the stored Restricted artifact and the network; ownership and token validity are re-checked on every request.
- **Zero Trust Consideration**: Every download request is authorized per-request against the owning user; a valid token alone never overrides ownership, and an indeterminate/expired/used token denies.

## Standards Alignment
- **OWASP ASVS**: V4.x (access control), V3.x (session), V8.x (data protection)
- **OWASP AISVS**: n/a (no AI component)
- **NIST SP 800-53**: AC-3 (access enforcement), AC-4 (information flow), SC-12/SC-28 (protection at rest), AU-2 (audit)
- **NIST SP 800-207**: per-request authorization; least standing access (single-use, expiring)
- **Regulatory**: GDPR Arts. 5(1)(f) integrity & confidentiality, 32 (security of processing), 15/20 (access/portability modalities)
- **Other**: `PRIV-1.17`, `PRIV-1.6`, `PRIV-1.9`, `SEC-6.1`, `SEC-8.1`, `SEC-5.6`

## Acceptance Criteria
1. **AC-01 (verbatim `PRIV-1.17`)**: Given an export download, when requested without the owner's authenticated session, after expiry, after first use, or for any other user, then the download is rejected.
2. **AC-02 (verbatim `PRIV-1.17`)**: Given the bounded retention window has elapsed or the owner has been erased, when storage is inspected, then no export artifact remains.
3. **AC-03**: Given an export download or generation, when performed, then it is rate-limited (013) and a DSR audit event is written (012).
4. **AC-04 (negative)**: Given a download token, when it is used a second time or after its expiry, then access is denied (single-use, time-bounded) and no artifact bytes are served.
5. **AC-05 (negative)**: Given an attacker enumerates artifact or token identifiers, when they request them, then identifiers are unguessable and every non-owner request returns not-found/forbidden with no artifact disclosure.

## Failure Behavior
- **On Invalid Input**: Reject with HTTP 403 (non-owner/unauthenticated) or 404 (unknown/expired/used token); never disclose whether the artifact exists for another user.
- **On System Error**: Fail closed — if ownership, token validity, or session cannot be confirmed, deny the download.
- **Alerting**: A burst of failed/forbidden download attempts or token-enumeration patterns raises a security alert (no token contents, no PII).

## Test Strategy
- **Unit Tests**: Token issuance (unguessable, single-use, TTL), validation (expired/used/forged → deny), owner binding.
- **Integration Tests**: Owner can download within session/valid token; other user, unauthenticated, expired, and re-used requests all denied; artifact removed after retention and after erasure (maps to TEST-1.4).
- **Security Tests**: IDOR/enumeration fuzz on artifact and token identifiers; replay of a consumed token; cross-user access returns not-found/forbidden (maps to TEST-1.3 cross-user isolation).
- **Compliance Tests**: Automated evidence that no artifact persists past the retention window or past owner erasure, and that each download/generation is audited.
- **Coverage Target**: ≥ 80% branch coverage of the download/token module.

## Dependencies
- **Upstream**: 046 (export generation produces the artifact), 019 (session management), 014 (authorization decision point), 013 (rate limiting), 012 (audit log), 011 (encryption at rest for the stored artifact), 051 (retention job deletes expired artifacts).
- **Downstream**: 050 (DSR endpoints link to the secured download), 048 (erasure removes any outstanding artifact).
- **External**: None (artifact storage backend `TO BE DECIDED`; keep behind an interface, default to encrypted, key-separated, owner-scoped storage).

## Implementation Notes
- **Constraints**: Tokens generated with a CSPRNG, single-use, short TTL (minutes), bound to the owning user and the specific artifact; artifact encrypted at rest (`SEC-5.6`). Download served only over TLS 1.3.
- **Anti-Patterns**: MUST NOT issue a long-lived, unauthenticated, or enumerable URL; MUST NOT serve bytes on an expired/used token; MUST NOT leak artifact existence across users; MUST NOT retain the artifact past the bounded window or past owner erasure.
- **AI Development Guidance**: **Recommended model: Opus 4.8.** A high-value access-control chokepoint where an IDOR/replay/enumeration slip is directly exploitable; favor the strongest adversarial reasoning on token-lifecycle and authorization edge cases. Mandatory human security review before merge; keep the artifact-handoff contract in sync with issue 046.
