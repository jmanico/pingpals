# Requirement: Privacy center UI (consent management, export, erasure, DSR actions)

## Metadata
- **ID**: REQ-FE-063
- **Title**: Privacy center UI — consent grant/withdraw, data export + access-controlled download, erasure, DSR actions
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Medium
- **Classification**: Privacy

## Requirement
- **Description**: The frontend MUST provide a privacy center where the authenticated user can: manage per-channel consent (grant/withdraw, recorded as immutable events via issue 045); request a machine-readable data export and download it only through an access-controlled, owner-authenticated, expiring/single-use link (issue 047); and request account erasure behind an explicit, unambiguous confirmation that triggers the server-side hard-delete cascade (issue 048). It MUST surface the remaining data-subject-rights / DSR actions (access, rectification, restriction, objection — issue 050). The export download link MUST NOT be rendered as a long-lived, unauthenticated, or enumerable URL, and every DSR action is rate-limited and audited server-side.
- **Rationale**: Surfaces `PRIV-1.2`/`PRIV-1.3`/`PRIV-1.5`/`PRIV-1.6`/`PRIV-1.17` to the user — the GDPR rights center. Export artifacts are Restricted (`PRIV-1.17`) and erasure is irreversible (`PRIV-1.6`), so the UI must enforce strong confirmation and never expose a downloadable artifact outside the owner's authenticated context.
- **Design**: Per `DESIGN.md` §7, the privacy center is a calm, token-styled set of cards on Parchment using DESIGN §6 voice that is reassuring but unambiguous. The irreversible erasure action is clearly destructive (`--color-danger`, icon+label, not color alone — DESIGN §3.4) behind a deliberate confirmation (typed confirmation or explicit checkbox), distinct from gentle everyday actions. Consent controls mirror issue 062. Focus uses the Gilt ring; the King Ping mascot may anchor a "your data, your reign" framing (DESIGN §1).

## Scope
- **Applies To**: Web App
- **Components**: React 19 SPA — consent management panel, export request + download affordance, erasure request + confirmation, DSR actions panel; consumes API client (057), Zod (056), component library (064), consent store (045), export (046/047), erasure (048), DSR endpoints (050).
- **Actors**: Authenticated user (owner) exercising rights over their own data set only.
- **Data Classification**: Restricted (consent records, export artifact containing all personal data, erasure scope).

## Security Context
- **Defense Layer**: Access control (owner-only export download) + fail-closed authorization + audited privacy actions.
- **Threat(s) Addressed**: Unauthorized access to an export artifact via guessable/long-lived URL (CWE-639/CWE-200, `PRIV-1.17`), accidental or unauthorized erasure (data-integrity / availability), consent tampering (mitigated by immutable events `PRIV-1.15`), DSR-endpoint abuse/flooding (mitigated by server rate limits `SEC-6.1`). STRIDE: Information Disclosure, Tampering, Repudiation, Denial of Service.
- **Trust Boundary**: Client-server edge. All DSR actions are authorized, executed, and audited server-side (045/047/048/050); the UI initiates them within the owner's authenticated session and never holds or exposes the artifact outside that session.
- **Zero Trust Consideration**: The export download is treated as Restricted and reachable only via the owner's authenticated session or a short-lived single-use token (`PRIV-1.17`); the UI assumes no implicit authority — every DSR action re-authorizes server-side and fails closed.

## Standards Alignment
- **OWASP ASVS**: V4 (access control), V8 (data protection / privacy), V13 (API)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: AC-3 (access enforcement), AU-2 (audit of DSR actions — server), SI-12 (information handling)
- **NIST SP 800-207**: per-request authorization for every DSR action
- **Regulatory**: GDPR Arts. 15, 16, 17, 18, 20, 21 (access, rectification, erasure, restriction, portability, objection), Art. 7 (consent)
- **Other**: `PRIV-1.2`, `PRIV-1.3`, `PRIV-1.5`, `PRIV-1.6`, `PRIV-1.15`, `PRIV-1.17`

## Acceptance Criteria
1. **AC-01**: Given the privacy center, when the user grants or withdraws a per-channel consent, then it is recorded as a distinct immutable event via 045 and reflected in the UI (`PRIV-1.2`).
2. **AC-02**: Given the user requests a data export, when generated, then the artifact is machine-readable and the UI exposes it only via an owner-authenticated, expiring, single-use download — not a long-lived, unauthenticated, or enumerable URL. *(verbatim `PRIV-1.17`: an export download is rejected without the owner's authenticated session, after expiry, after first use, and for any other user.)*
3. **AC-03**: Given the user requests erasure, when confirmed via an explicit unambiguous confirmation, then the server-side hard-delete cascade (048) is triggered and the UI reflects completion. *(verbatim `PRIV-1.6`: erasure MUST be a hard delete that cascades …)*
4. **AC-04**: Given the DSR panel, when shown, then access, rectification, restriction, and objection actions (050) are available to the owner (`PRIV-1.3`).
5. **AC-05 (negative)**: Given an export download link, when accessed without the owner's authenticated session, after expiry, after first use, or by another user, then it is denied (the UI never renders a reusable/enumerable artifact URL).
6. **AC-06 (negative)**: Given the erasure action, when the user has not completed the explicit confirmation, then no erasure request is sent (no accidental irreversible deletion).
7. **AC-07 (accessibility)**: Given the privacy center, when rendered, then the destructive erasure pairs color with icon+label, all actions are keyboard-operable with a visible Gilt focus ring, confirmations are programmatically announced, and contrast meets WCAG 2.2 AA (`NFR-1.4`, DESIGN §3.4).

## Failure Behavior
- **On Invalid Input**: An incomplete erasure confirmation sends nothing; a malformed DSR request is rejected field-level with a gentle error.
- **On System Error**: Fail closed — a failed export/erasure/DSR call surfaces an error and does not show the action as complete; an unverifiable download link denies access rather than serving the artifact (`PRIV-1.17`).
- **Alerting**: n/a at UI layer; DSR actions, export, and erasure are rate-limited (`SEC-6.1`) and audited (`SEC-8.1`, `PRIV-1.16`) server-side.

## Test Strategy
- **Unit Tests**: Consent grant/withdraw invokes the distinct consent action; erasure is gated on explicit confirmation; export download affordance uses an owner-session/single-use token, never a static URL; DSR actions render and dispatch.
- **Integration Tests**: Request export → authenticated single-use download succeeds once and is denied on reuse/expiry/other-user (with 047); erasure confirmation triggers cascade (048) and reflects completion; consent events recorded (045).
- **Security Tests**: Attempt export download without session / after first use / as another user and assert denial (maps to PRIV-1.17); attempt erasure without confirmation and assert no request sent.
- **Compliance Tests**: Evidence the UI exposes all DSR rights (`PRIV-1.3`) and that consent changes produce auditable events (`PRIV-1.2`).
- **Coverage Target**: ≥ 80% branch coverage of privacy-center components.

## Dependencies
- **Upstream**: 054 (scaffold), 056 (Zod), 057 (API client), 064 (component library), 005 (tokens), 045 (consent store), 046 (data export), 047 (export artifact access control), 048 (erasure cascade), 050 (DSR endpoints), 062 (shared consent surface).
- **Downstream**: None (terminal user-facing surface for DSR).
- **External**: None directly (server mediates all artifacts).

## Implementation Notes
- **Constraints**: Export download must be owner-authenticated, expiring, single-use, non-enumerable (`PRIV-1.17`) — the UI never embeds a static artifact URL. Erasure requires explicit unambiguous confirmation and is irreversible (`PRIV-1.6`). Consent changes are distinct audited events (`PRIV-1.2`, `PRIV-1.15`). All DSR actions are server-authorized, rate-limited, and audited. All styling via tokens (005).
- **Anti-Patterns**: MUST NOT render a long-lived/unauthenticated/enumerable export URL (`PRIV-1.17`); MUST NOT trigger erasure without explicit confirmation; MUST NOT set consent via a general write (`PRIV-1.15`); MUST NOT show a DSR action as complete before server confirmation; MUST NOT hard-code styling (DESIGN §7.1).
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** A rights-center UI over well-specified DSR endpoints is broad, conventional work. Mandatory human privacy/security review of the export-download access-control affordance and the erasure-confirmation gate before merge, given the irreversible/Restricted nature of these actions.
