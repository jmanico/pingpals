# Requirement: Category & cadence UI (categories, default/override cadence, quiet hours, timezone)

## Metadata
- **ID**: REQ-FE-060
- **Title**: Category and cadence configuration UI — defaults, per-contact override, quiet hours, timezone, send window
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: Medium
- **Classification**: Functional

## Requirement
- **Description**: The frontend MUST provide UI to manage relationship categories and their default cadences, to set a per-contact cadence override that takes precedence over the category default, and to configure quiet hours, the user's timezone, and an optional send-time window (and optional preferred day of week). Cadence MUST be expressed as a positive interval in days. Deleting a category MUST drive a reassignment-of-contacts UX that fails closed: the delete MUST NOT complete if any contact would be left without a category (the constraint is enforced server-side in issue 026; the UI MUST require the user to pick a destination category first). All inputs MUST be Zod-validated (056) and rejected field-level on failure (reject over sanitize).
- **Rationale**: Surfaces `FR-2.1`–`FR-2.3` (default + custom categories, reassignment-on-delete) and `FR-3.1`–`FR-3.3` (interval-in-days cadence, per-contact override precedence, quiet hours, timezone). Timezone is safety-relevant: the scheduler fails closed to no delivery when timezone is unknown (`FR-3.3`), so the UI must make the timezone explicit and required.
- **Design**: Per `DESIGN.md` §7, categories render as token-colored chips/cards on Parchment; the shipped defaults (Best Friend, Casual Friend, Family, Professional — `FR-2.1`) are presented with the crown accent for "royal" defaults (DESIGN §5). Cadence and quiet-hours controls use the component library (064) with Gilt focus rings; the reassignment dialog uses DESIGN §6 voice and pairs the destructive delete with icon+label (`--color-danger`, not color alone, DESIGN §3.4).

## Scope
- **Applies To**: Web App
- **Components**: React 19 SPA — category manager (create/rename/delete + default cadence), per-contact cadence override control, quiet-hours/timezone/send-window settings, reassignment dialog; consumes API client (057), Zod (056), component library (064).
- **Actors**: Authenticated user (owner) configuring only their own categories and cadences.
- **Data Classification**: Restricted (category and cadence are tied to contacts / personal data and preferences).

## Security Context
- **Defense Layer**: Input Validation (bounded positive intervals, timezone presence) + fail-closed UX.
- **Threat(s) Addressed**: Orphaned-contact integrity break on category delete (CWE-20 / data-integrity, mitigated by reassignment), out-of-range/negative cadence driving runaway scheduling (abuse intent of `SEC-6.x`), unknown-timezone delivery at wrong hours. STRIDE: Tampering, Denial of Service (scheduler load).
- **Trust Boundary**: Client-server edge. Server enforces the reassignment constraint and quota/cadence bounds (026/029/027); the UI guides the user to a valid submission and never bypasses the server constraint.
- **Zero Trust Consideration**: The UI treats all settings input as untrusted and bounded; it does not assume a delete is safe — it requires a destination category and lets the server make the authoritative fail-closed decision.

## Standards Alignment
- **OWASP ASVS**: V5.1 (input validation), V11.1 (business-logic limits)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SI-10 (input validation)
- **NIST SP 800-207**: server-side authoritative constraint enforcement
- **Regulatory**: n/a
- **Other**: `FR-2.1`, `FR-2.2`, `FR-2.3`, `FR-3.1`, `FR-3.2`, `FR-3.3`, `FE-1.2`

## Acceptance Criteria
1. **AC-01**: Given the category manager, when first loaded, then it shows the shipped defaults Best Friend, Casual Friend, Family, Professional, each with a configurable default cadence. *(verbatim `FR-2.1`: default categories each with a configurable default cadence.)*
2. **AC-02**: Given a user creates/renames a custom category, when saved, then it has its own configurable default cadence (`FR-2.2`).
3. **AC-03**: Given a contact with a per-contact cadence override, when its effective cadence is shown, then the override takes precedence over the category default. *(verbatim `FR-3.2`: a per-contact override MUST take precedence.)*
4. **AC-04 (negative)**: Given a category delete, when any contact would be left without a category, then the UI requires reassignment first and the delete fails closed (no orphaned contact). *(verbatim `FR-2.3`: deleting a category MUST require reassignment and MUST fail closed if any contact would be left without a category.)*
5. **AC-05 (negative)**: Given a cadence input that is zero, negative, or non-integer, when submitted, then it is rejected field-level (positive interval in days only, `FR-3.1`) with no write.
6. **AC-06**: Given quiet hours and timezone settings, when saved, then a timezone is required; an unset/unknown timezone is surfaced as required because the scheduler fails closed to no delivery without it (`FR-3.3`).
7. **AC-07 (accessibility)**: Given the category and settings UI, when rendered, then controls are labeled, the destructive delete pairs color with icon+label, focus is visible, and contrast meets WCAG 2.2 AA (`NFR-1.4`, DESIGN §3.4).

## Failure Behavior
- **On Invalid Input**: Reject field-level (non-positive cadence, missing timezone, missing reassignment target) with no submission; gentle non-blaming server-error surfacing.
- **On System Error**: Fail closed — a failed category delete leaves all contacts categorized; the UI never shows a delete as complete unless the server confirms reassignment succeeded.
- **Alerting**: n/a at UI layer.

## Test Strategy
- **Unit Tests**: Defaults rendered; custom category create/rename with own cadence; override precedence shown; non-positive/non-integer cadence rejected; timezone required; reassignment required before delete enabled.
- **Integration Tests**: Category delete with reassignment succeeds; delete without a destination is blocked client-side and rejected server-side (026); cadence and quiet-hours/timezone persist via API (027).
- **Security Tests**: Attempt to submit a category delete that would orphan a contact and assert fail-closed; out-of-range cadence rejected (maps to FR-3.1 bounds).
- **Compliance Tests**: n/a
- **Coverage Target**: ≥ 80% branch coverage of category/cadence/settings components.

## Dependencies
- **Upstream**: 054 (scaffold), 056 (Zod), 057 (API client), 064 (component library), 005 (tokens), 026 (category CRUD + reassignment constraint), 027 (cadence config API), 059 (contacts to assign/override).
- **Downstream**: 061 (reminder card reflects effective cadence), 031 (scheduler consumes cadence/timezone), 062 (per-category channel overrides reference categories).
- **External**: A timezone source — prefer the platform `Intl`/IANA timezone list; no third-party library without `SEC-9.1` vetting.

## Implementation Notes
- **Constraints**: Cadence is a positive integer of days (`FR-3.1`); per-contact override precedence (`FR-3.2`); timezone required because the scheduler fails closed without it (`FR-3.3`). Category delete is gated on a chosen reassignment target (`FR-2.3`); the authoritative fail-closed check is server-side (026). All styling via tokens (005).
- **Anti-Patterns**: MUST NOT allow a category delete that orphans a contact (`FR-2.3`); MUST NOT accept zero/negative/non-integer cadence (`FR-3.1`); MUST NOT let the user save settings without a timezone (`FR-3.3`); MUST NOT bypass the server constraint with a client-only delete; MUST NOT hard-code styling (DESIGN §7.1).
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Form-and-settings UI against a clear constraint set is broad, conventional work. Human review must confirm the fail-closed reassignment gate and the required-timezone behavior align with the scheduler's fail-closed contract (`FR-3.3`).
