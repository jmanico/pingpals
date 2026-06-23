# Requirement: Single source-of-truth design-token file (palette, type, spacing, radii)

## Metadata
- **ID**: REQ-FND-005
- **Title**: Centralized design tokens consumed by all components, with WCAG AA contrast pairings
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Functional

## Requirement
- **Description**: The SPA MUST ship a single source-of-truth design-token file (CSS custom properties and/or a `tokens.ts`) that defines the full brand palette, semantic status colors, the type scale, spacing, and radii as named tokens. ALL components MUST consume these tokens and MUST NOT use hard-coded color/size/spacing values. The token set MUST encode the WCAG 2.2 AA contrast pairings of `DESIGN.md` §3.4 (e.g. Plum Ink on Parchment for body text) and MUST NOT permit a known-failing pairing (e.g. Royal Gold body text on cream) as a body-text token.
- **Rationale**: `DESIGN.md` §7.1 requires one centralized token source so rebranding and theming stay centralized; `CLAUDE.md` mandates "design tokens only" for styling. Centralization also enforces accessibility (`NFR-1.4`, WCAG 2.2 AA) and the brand rules (purple lead, gold accent only — `DESIGN.md` §3.2). Exact hex values are pending a color-pick against vector source art (`DESIGN.md` §9), so tokens are defined by name now and final hex locked later — this issue is non-blocking on that color-pick.
- **Design**: This issue *is* the design-system substrate of `DESIGN.md` §3 (color), §4 (typography/type scale), §5 (motifs use token colors), and §7/§7.1 (UI application). Focus state uses a Gilt focus ring meeting 3:1 non-text contrast (`DESIGN.md` §7); status MUST never be conveyed by color alone (pair with icon/label — §3.4) — tokens support but do not replace that rule.

## Scope
- **Applies To**: Web App
- **Components**: React 19 SPA — `tokens` module (CSS custom properties / `tokens.ts`) consumed by every styled component (reminder card, buttons, surfaces, focus states).
- **Actors**: End user (visual consumer; accessibility beneficiary), developers building UI.
- **Data Classification**: Public/Internal (tokens carry brand values, no personal data).

## Security Context
- **Defense Layer**: Architecture (styling discipline) — not a primary security control, but supports CSP compliance.
- **Threat(s) Addressed**: Indirectly supports `FE-1.4` strict CSP (no inline styles/handlers) by centralizing style in token-driven classes rather than inline attributes; reduces drift that could reintroduce inline style. STRIDE: n/a (no direct trust boundary).
- **Trust Boundary**: None directly; tokens are static client assets. They MUST be served under the same strict-CSP, SRI/self-host posture as other client assets (`FE-1.4`, `FE-1.8`).
- **Zero Trust Consideration**: Tokens are static and contain no user input; no validation needed. They MUST NOT be sourced from an untrusted third-party CDN without SRI/self-hosting (`FE-1.8`).

## Standards Alignment
- **OWASP ASVS**: n/a (presentation tokens), supports V14.4 (HTTP security headers/CSP) indirectly
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: n/a
- **NIST SP 800-207**: n/a
- **Regulatory**: Accessibility — WCAG 2.2 AA per `NFR-1.4`
- **Other**: `DESIGN.md` §3 (palette), §3.3 (semantic colors), §3.4 (accessibility, normative), §4.2 (type scale), §5, §7, §7.1, §9 (open hex values), `FE-1.4`, `FE-1.8`

## Acceptance Criteria
1. **AC-01**: Given the token file, when inspected, then it defines all core brand tokens (`--color-purple-900/700/500`, `--color-gold-500/300`, `--color-cream-50`, `--color-white`, `--color-ink-900`), all semantic tokens (`--color-success/warning/danger/info`), the type scale (2.5/2.0/1.5/1.25/1.0/0.875/0.75 rem roles), spacing, and radii — by name.
2. **AC-02**: Given any styled component, when reviewed, then it references tokens only and contains no hard-coded hex/size/spacing literal. *(maps `DESIGN.md` §7.1 / `CLAUDE.md` "design tokens only".)*
3. **AC-03**: Given the default body-text pairing, when contrast is computed, then Plum Ink on Parchment meets WCAG 2.2 AA (≥4.5:1), and the Gilt focus ring meets ≥3:1 non-text contrast. *(verifies `DESIGN.md` §3.4 / `NFR-1.4`.)*
4. **AC-04 (negative)**: Given a request to use Royal Gold as body-text color on a light background, when validated against the token rules, then no body-text token resolves to that failing pairing (gold is accent/shape/border or text-on-deep-purple only). *(maps `DESIGN.md` §3.4: "gold text on cream fails contrast".)*
5. **AC-05**: Given exact hex values are still pending (`DESIGN.md` §9), when a hex is later locked, then only the token file changes and consuming components need no edits (centralization holds).

## Failure Behavior
- **On Invalid Input**: n/a (static tokens). A component using a non-token literal MUST fail a lint/CI check (003) rather than ship.
- **On System Error**: n/a runtime. Missing token file is a build error, not a runtime fallback to hard-coded values.
- **Alerting**: CI lint failure on any hard-coded styling literal; contrast-check failure on any defined body-text pairing.

## Test Strategy
- **Unit Tests**: Automated contrast computation over defined text/background token pairings asserts WCAG 2.2 AA (4.5:1 body, 3:1 large/UI); a lint rule asserts no component hard-codes style values.
- **Integration Tests**: Render representative components (button, reminder card, focus state) and assert computed styles resolve from tokens.
- **Security Tests**: Confirm tokens load under strict CSP with no inline style/handler and, if remotely hosted, with SRI (`FE-1.4`, `FE-1.8`).
- **Compliance Tests**: Accessibility check (axe or equivalent) over token-driven components confirms WCAG 2.2 AA contrast (`NFR-1.4`).
- **Coverage Target**: ≥ 80% branch coverage of any token-resolution/contrast-check helper code.

## Dependencies
- **Upstream**: 001 (SPA module that houses the token file).
- **Downstream**: 055 (disabled/`#` link affordance uses tokens) and every UI component issue (reminder card, contact views, buttons, focus states).
- **External**: Web fonts (Cinzel/Trajan, Playfair Display, Inter, Poppins) — loaded with SRI or self-hosted (`FE-1.8`); font licensing is an open question (`DESIGN.md` §9), not resolved here.

## Implementation Notes
- **Constraints**: Exact hex values are approximate pending color-pick (`DESIGN.md` §3 intro, §9) — define tokens by name and treat hex as provisional; do NOT block on the color-pick. Dark mode is deferred (`DESIGN.md` §9) — structure tokens to allow a future theme without committing one now. Keep tokens as the single source of truth (`DESIGN.md` §7.1).
- **Anti-Patterns**: MUST NOT hard-code colors/sizes/spacing in components (`CLAUDE.md`, `DESIGN.md` §7.1); MUST NOT define a body-text token that fails AA contrast (`DESIGN.md` §3.4); MUST NOT convey status by color alone (pair with icon/label); MUST NOT introduce inline styles/handlers (`FE-1.4`); MUST NOT pull fonts/tokens from a third-party CDN without SRI or self-hosting (`FE-1.8`).
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Token-file authoring and type-scale/spacing definition is a deterministic, design-spec-driven task suited to a strong generalist; the accessibility math is well-defined. Human review MUST confirm AA contrast on all body pairings and that no failing gold-on-cream body token exists.
