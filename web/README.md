# Pingpals Web (React 19 SPA)

Client-only React 19 SPA (no SSR, function components + hooks). This module ships the design-token
source of truth (`src/tokens/` — REQ-FND-005) and the build/runtime scaffolding. The full
application (strict CSP, SRI, Zod validation, `validateAndSanitizeUrl`, AbortController fetch,
UUID keys) is built in the FRONTEND issues, starting with issue 054.

## Layout

```
web/
  package.json          # manifest (exact-pinned deps)
  package-lock.json     # integrity-hash-pinned lockfile (npm ci) — REQ-FND-004
  Dockerfile            # hardened multi-stage; non-root nginx static serve — REQ-FND-002
  src/tokens/           # design tokens (tokens.ts + tokens.css) — REQ-FND-005
  src/main.tsx          # SPA entrypoint placeholder
```

## Design tokens (REQ-FND-005)

`src/tokens/tokens.ts` is the single source of truth; `tokens.css` mirrors it as CSS custom
properties. Components consume tokens only — never hard-coded color/size/spacing literals
(DESIGN.md §7.1). `tokens.test.ts` enforces the WCAG 2.2 AA contrast pairings (DESIGN.md §3.4).

## Local checks

`../scripts/ci-web.sh` runs typecheck, `npm audit`, and `vitest`.
