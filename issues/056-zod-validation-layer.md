# Requirement: Zod validation layer for all form input and all API responses

## Metadata
- **ID**: REQ-FE-056
- **Title**: Client-side Zod validation of every form input and every API response (fail closed)
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Security

## Requirement
- **Description**: The frontend MUST validate all form input and all API response data with Zod before that data is used or rendered. Client schemas MUST mirror the server-side input bounds (issue 009) — same maximum string lengths, collection cardinalities, numeric ranges, and field sets — and MUST reject unknown fields rather than passing them through. An API response that fails its Zod schema MUST fail closed: the client MUST NOT render or act on unvalidated data; it MUST surface a gentle error and treat the response as unusable. Validation MUST occur at the boundary (on receipt of the response / on form submit), not lazily at render time.
- **Rationale**: The React client treats provider/API responses as untrusted (ARCH Dependency Rule 2, Zero Trust inside the boundary). Validating with Zod before use satisfies `FE-1.2` and prevents malformed or attacker-influenced data from reaching the DOM or driving client logic. Mirroring server bounds (009) keeps a single conceptual schema and avoids a client that accepts what the server would reject.
- **Design**: Validation failures present through the shared component library (issue 064) using DESIGN §6 voice — gentle, non-blaming ("That didn't go through…") — but MUST NOT soften a field-level validation error into ambiguity (`FR-1.4`, DESIGN §6 note). Field-level errors render inline beside the offending input using token-driven `--color-danger` styling (DESIGN §3.3), paired with text/icon so color is not the sole signal (DESIGN §3.4).

## Scope
- **Applies To**: Web App
- **Components**: React 19 SPA — shared `lib/schemas` (Zod) module and a typed `parse`/`safeParse` wrapper consumed by the API client (057) and every form.
- **Actors**: Authenticated user (owner) supplying form input; the API as an untrusted response source.
- **Data Classification**: Restricted (forms and responses carry contact personal data, consent, cadence); schemas describe but do not persist it.

## Security Context
- **Defense Layer**: Input Validation (client-side schema enforcement, reject-on-failure).
- **Threat(s) Addressed**: Rendering of malformed/unexpected API data (CWE-20), mass-assignment of unknown fields (CWE-915), type-confusion driving client logic, prototype-pollution via untrusted keys. STRIDE: Tampering, Elevation of Privilege.
- **Trust Boundary**: Client edge of the client-server boundary — the point where bytes from the API become typed application data. The server is the authoritative validator (009); this is the independent client gate (defense in depth), not a replacement for it.
- **Zero Trust Consideration**: API responses are treated as untrusted and re-validated client-side; the client never assumes a response is well-formed because it came from "our" server.

## Standards Alignment
- **OWASP ASVS**: V5.1 (input validation), V5.1.3 (schema validation), V13 (API data validation)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SI-10 (information input validation)
- **NIST SP 800-207**: untrusted-input handling inside the boundary
- **Regulatory**: n/a
- **Other**: `FE-1.2`, `FR-1.4`, `SEC-4.1`, ARCH Dependency Rule 2

## Acceptance Criteria
1. **AC-01**: Given a form submission, when the input is validated, then it is parsed by a Zod schema whose bounds match the server schema (009) before any request is sent; an out-of-bounds field is rejected with an inline field-level error and no request is made. *(verbatim `FR-1.4`: an invalid phone or email is rejected with a field-level error and no partial write occurs.)*
2. **AC-02**: Given an API response, when received, then it is validated with Zod before use, and a response with an unknown/extra field is rejected (unknown fields are not passed through). *(verbatim `FE-1.2`: all API response data MUST be validated with Zod before use.)*
3. **AC-03 (negative)**: Given an API response that fails its Zod schema, when processed, then the client renders no part of that unvalidated data and surfaces a gentle non-blaming error (fail closed).
4. **AC-04 (negative)**: Given a form value exceeding its declared maximum length or cardinality, when submitted, then it is rejected, never truncated or coerced (reject over sanitize).
5. **AC-05 (accessibility)**: Given a field-level validation error, when rendered, then the message is programmatically associated with its input (e.g. `aria-describedby`), conveyed by text not color alone, and meets WCAG 2.2 AA contrast (`NFR-1.4`, DESIGN §3.4).

## Failure Behavior
- **On Invalid Input**: Reject at the boundary; show an inline field-level error (forms) or a gentle global error (responses); perform no request and render no unvalidated data. Do not leak schema internals or raw response bodies.
- **On System Error**: Fail closed — any parse exception is treated as a validation failure (data unusable), never as "assume valid".
- **Alerting**: A spike in API-response schema failures MAY raise a frontend-health alert (possible server contract drift); no PII in the signal.

## Test Strategy
- **Unit Tests**: Per-schema table tests for accepted and rejected inputs, boundary values (min/max length, cardinality, numeric range), unknown-field rejection, and that `safeParse` failure yields a fail-closed result.
- **Integration Tests**: Submit each form with valid and invalid data; feed each API consumer a malformed response and assert nothing unvalidated renders.
- **Security Tests**: Fuzz response payloads (extra fields, wrong types, oversized strings) and assert no unvalidated value reaches the DOM; cross-check client bounds equal server bounds (009).
- **Compliance Tests**: n/a
- **Coverage Target**: ≥ 80% branch coverage of the schema/parse module.

## Dependencies
- **Upstream**: 054 (SPA scaffold), 009 (server input-validation bounds the client mirrors), 064 (component library renders the errors).
- **Downstream**: 057 (API client validates every response through this layer), 058–063 (every feature form/response consumer uses these schemas).
- **External**: Zod — vetted per `SEC-9.1`, pinned with integrity (`SEC-9.3`) before adoption.

## Implementation Notes
- **Constraints**: Schemas are the single client-side source of truth and MUST stay in sync with server bounds (009) — drift is a defect. Use `safeParse` (never throw into render). Apply a length cap conceptually before expensive checks; keep schemas free of catastrophic-backtracking regex (mirror `SEC-4.x` ReDoS guidance).
- **Anti-Patterns**: MUST NOT render API data before validation; MUST NOT pass through unknown fields (no mass-assignment, SECURITY §4); MUST NOT truncate/coerce over-limit input (reject over sanitize, `FR-1.4`); MUST NOT treat a parse exception as "valid"; MUST NOT duplicate divergent bounds from the server.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Schema authoring is repetitive, well-specified work mirroring an existing server contract — broad and mechanical rather than novel. Human review must confirm client bounds equal the server bounds in issue 009 and that response failure paths truly fail closed.
