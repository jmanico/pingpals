# Pingpals issue backlog

Decomposition of the four authoritative specs (`REQUIREMENTS.md`, `ARCHITECTURE.md`,
`SECURITY.md`, `DESIGN.md`) into one epic + 79 single-responsibility sub-issues, each authored
against `REQUIREMENT_TEMPLATE.md` and ready for `gh issue create`.

## Files

- `EPIC.md` — parent epic body. Contains the objective, model-recommendation legend, dependency
  flow, and a `<!-- TASKLIST -->` marker that `create-issues.sh` replaces with a task list
  linking the real sub-issue numbers.
- `NNN-*.md` — one fully-templated sub-issue per file (zero-padded, creation order).
- `labels.sh` — creates/updates the label taxonomy (`gh label create … --force`). **Run first.**
- `create-issues.sh` — creates every sub-issue, then the epic with a backfilled task list.

## Run

```bash
# 1. Ensure labels exist
bash issues/labels.sh

# 2. Preview exactly what will be created (creates nothing)
bash issues/create-issues.sh --dry-run

# 3. Create for real (sub-issues first, then the epic)
bash issues/create-issues.sh
```

Override the target repo with `REPO=owner/name bash issues/...`. Default: `jmanico/pingpals`.
`create-issues.sh` is **not** idempotent — run it once; re-running creates duplicates.

## Model recommendation legend

Each issue's *Implementation Notes → AI Development Guidance* names the recommended model:

- **Opus 4.8** — security/crypto/auth/audit/GDPR-correctness and other threat-sensitive logic
  where a subtle error is a vulnerability.
- **ChatGPT 5.5** — well-bounded CRUD, schema/DTO definitions, UI scaffolding, design-token /
  config / CI plumbing, and documentation.

Advisory only; both models can complete any issue.

## Groups

| Prefix | Area | Issues |
|---|---|---|
| `[FOUNDATION]` | repo, tooling, CI, tokens, crypto inventory | 001–006 |
| `[BACKEND]` | Flask core platform / cross-cutting controls | 007–016 |
| `[AUTH]` | OIDC, session, WebAuthn, OAuth | 017–023 |
| `[CONTACTS]` | contacts, categories, cadence, import | 024–030 |
| `[ENGINE]` | reminder scheduler | 031–034 |
| `[DELIVERY]` | delivery worker, channels, outreach links | 035–044 |
| `[PRIVACY]` | consent, export, erasure, retention, DSR | 045–053 |
| `[FRONTEND]` | React 19 SPA | 054–064 |
| `[TESTING]` | test suites + coverage gates | 065–068 |
| `[DECISION]` | open infra/process decisions (no code) | 069–075 |
| `[LATER]` | later-phase tracking | 076–079 |
