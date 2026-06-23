# Requirement: Contact management UI (list/create/edit/delete with category assignment)

## Metadata
- **ID**: REQ-FE-059
- **Title**: Contact management UI — CRUD with category assignment, field-level reject, safe outreach links
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Functional

## Requirement
- **Description**: The frontend MUST provide UI to list, create, edit, and delete contacts owned by the authenticated user, each assigned to exactly one category. A contact MUST be creatable with at minimum a display name, all other fields optional. Every contact field MUST be Zod-validated (056) against the server schema (009/024) and an invalid field (e.g. phone, email) MUST be rejected with an inline field-level error and no submission — never coerced. Any outreach link rendered from a contact (phone/email/handle) MUST be passed through `validateAndSanitizeUrl` (055), rendering `"#"` if invalid. Deletion MUST present a clear confirmation and, on success, reflect that the contact and its associated data are removed (the cascade is enforced server-side, issue 025).
- **Rationale**: This is the primary surface for `FR-1.1`–`FR-1.4` (create with name-only minimum, edit/delete, reject-over-sanitize validation) and `FR-2.4` (exactly one category). It depends on but does not re-implement the server cascade (025) and per-user scoping (`SEC-2.2`).
- **Design**: Per `DESIGN.md` §7, contacts render as white cards on Parchment with generous spacing (DESIGN §7 density); the empty state shows the King Ping mascot with the voice-aligned copy "The court is quiet. Add your first pal to begin your reign." (DESIGN §6). Category is shown as a token-colored chip; the primary "Add pal" action is a Royal Purple button (DESIGN §7). The notes field shows the point-of-entry special-category-data advisory (`PRIV-1.18`). Destructive delete uses `--color-danger` with an icon+label (color not sole signal, DESIGN §3.4).

## Scope
- **Applies To**: Web App
- **Components**: React 19 SPA — contact list, contact create/edit form, delete confirmation, category-picker; consumes API client (057), Zod schemas (056), URL validator (055), component library (064).
- **Actors**: Authenticated user (owner) managing only their own contacts; contacts are third-party data subjects (not users).
- **Data Classification**: Restricted (contact name, phone, email, notes, category — personal data of third parties).

## Security Context
- **Defense Layer**: Input Validation (reject-over-sanitize) + Output Encoding (safe URL rendering, contextual escaping).
- **Threat(s) Addressed**: Injection via contact fields (CWE-20/CWE-79), malicious outreach URLs (`javascript:`/lookalike host, CWE-601, addressed by 055), cross-user data exposure (CWE-639, enforced server-side `SEC-2.2`). STRIDE: Tampering, Information Disclosure.
- **Trust Boundary**: Client-server edge. The UI renders only what the API returns for the owning user (ARCH Rule 1, `SEC-2.2`); it makes no scoping decision and re-validates all data (056) and all URLs (055) at render.
- **Zero Trust Consideration**: Contact-derived strings (notes, phone, handle) are untrusted even though they are "the user's own data"; they are validated on input and sanitized on output before any link sink.

## Standards Alignment
- **OWASP ASVS**: V5.1 (input validation), V5.3 (output encoding), V4 (access control — server side)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SI-10 (input validation), AC-3 (access enforcement — server)
- **NIST SP 800-207**: per-request authorization server-side; client presents only
- **Regulatory**: GDPR Arts. 5, 6, 25 (minimization, lawful basis surfaced via notes advisory `PRIV-1.18`)
- **Other**: `FR-1.1`, `FR-1.2`, `FR-1.3`, `FR-1.4`, `FR-2.4`, `FE-1.2`, `FE-1.3`, `PRIV-1.18`

## Acceptance Criteria
1. **AC-01**: Given the create form, when only a display name is provided, then the contact is created successfully (all other fields optional). *(verbatim `FR-1.1`: a contact with at minimum a display name; all other fields optional.)*
2. **AC-02 (negative)**: Given an invalid phone or email, when submitting, then it is rejected with a field-level error and no partial write occurs. *(verbatim `FR-1.4`: an invalid phone or email is rejected with a field-level error and no partial write occurs.)*
3. **AC-03**: Given a contact, when assigned a category, then it belongs to exactly one category at a time. *(verbatim `FR-2.4`: a contact MUST belong to exactly one category at a time.)*
4. **AC-04**: Given a contact with an outreach-able field, when its link is rendered, then the href passes `validateAndSanitizeUrl` (055) and an invalid one renders as `"#"`.
5. **AC-05**: Given a contact is deleted (with confirmation), when the server reports success, then the UI shows it removed and no longer lists it or its reminders (cascade per 025).
6. **AC-06 (negative)**: Given the contact list, when rendered, then it shows only the authenticated owner's contacts and never another user's data (server-scoped `SEC-2.2`).
7. **AC-07 (accessibility)**: Given the contact UI and its empty state, when rendered, then form fields have associated labels/errors, the delete affordance pairs color with icon+label, focus is visible (Gilt ring), and contrast meets WCAG 2.2 AA (`NFR-1.4`, DESIGN §3.4).

## Failure Behavior
- **On Invalid Input**: Inline field-level rejection with no submission (reject over sanitize, `FR-1.4`); a server-side rejection surfaces a gentle non-blaming error without leaking internals.
- **On System Error**: Fail closed — a failed save shows an error and does not optimistically show the contact as saved; a failed delete does not show the contact as removed.
- **Alerting**: n/a at UI layer; server logs DSR/deletion events (`SEC-8.1`).

## Test Strategy
- **Unit Tests**: Name-only create succeeds; invalid phone/email rejected inline; category picker enforces single selection; outreach link routed through 055; empty-state renders mascot + copy.
- **Integration Tests**: Create→edit→delete round trip against the API (024/025); confirm delete reflects cascade; confirm list shows only owner data when the API enforces scoping.
- **Security Tests**: Attempt cross-user contact access (expect not-found/forbidden from server, maps to SEC-2.2 test); inject a `javascript:` phone/handle and assert the rendered href is `"#"` (maps to FR-6.4/055).
- **Compliance Tests**: Confirm the notes special-category advisory (`PRIV-1.18`) is present at point of entry.
- **Coverage Target**: ≥ 80% branch coverage of contact UI components and form logic.

## Dependencies
- **Upstream**: 054 (scaffold), 055 (URL validator), 056 (Zod), 057 (API client), 064 (component library), 005 (tokens), 024 (contact CRUD API), 025 (deletion cascade), 026 (categories for the picker).
- **Downstream**: 060 (cadence override per contact), 061 (reminder card references contacts), 063 (privacy center may link to contact data).
- **External**: None directly (API client handles transport).

## Implementation Notes
- **Constraints**: Display name is the only required field (`FR-1.1`). All fields Zod-validated to server bounds (056/009). Exactly one category per contact (`FR-2.4`). All outreach links via 055; all styling via tokens (005). The cascade itself is server-side (025) — the UI only reflects it.
- **Anti-Patterns**: MUST NOT coerce/truncate invalid input (reject over sanitize, `FR-1.4`); MUST NOT render an unsanitized outreach href (`FE-1.3`/055); MUST NOT assume client-side scoping (server enforces `SEC-2.2`); MUST NOT optimistically show success before the server confirms; MUST NOT use array index keys for the contact list (`FE-1.6`); MUST NOT hard-code colors/spacing (DESIGN §7.1).
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Standard CRUD UI against well-specified schemas and an existing API contract — broad, conventional work. Human review must confirm reject-over-sanitize behavior, single-category enforcement, and that every outreach link routes through issue 055.
