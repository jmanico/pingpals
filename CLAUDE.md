# CLAUDE.md

Operating rules for Claude Code here. Do not duplicate the imported documents below — they are the source of truth.

## Project imports

Read and obey all four. **REQUIREMENTS.md wins** on any conflict.

@REQUIREMENTS.md
@ARCHITECTURE.md
@SECURITY.md
@DESIGN.md

## What this is

Pingpals is a single-user relationship-cadence reminder **web + API application**. See REQUIREMENTS.md §1–§2 for the product definition, scope, and the non-actor boundary.

## Bootstrap status

**Bootstrap mode**: no implementation exists yet. Stack is fixed and infrastructure is mostly `TO BE DECIDED` (ARCHITECTURE.md owns both). When a rule depends on an undecided choice, keep it behind an interface, default to the most restrictive option, and raise the open decision — do **not** invent the infrastructure.

## Working style

- **Read before you write.** A change must satisfy the relevant FR/SEC/PRIV/INT/FE/NFR tag. Cite the tag in commit messages and PR descriptions.
- **Fail closed.** If you cannot satisfy a security or privacy invariant, stop and surface it rather than shipping the weaker path (SEC-2.3).
- **Reject over sanitize** (SEC-4.1/FR-1.4; see SECURITY.md §4).
- **No new infrastructure decisions** without explicit human sign-off. Surface `TO BE DECIDED` items; don't resolve them silently.
- **Minimize dependencies** — vet each new library per SEC-9.x (see SECURITY.md §8).
- **Design tokens only** for styling (see DESIGN.md §7.1).

## GitHub issues — mandatory

**Every new GitHub issue MUST follow `REQUIREMENT_TEMPLATE.md`** (structured, testable requirement). Issues not framed against this template are out of process.

## Definition of done

A change is complete only when it:

1. Satisfies its requirement tag and the SECURITY.md rules in scope.
2. Has tests covering the relevant TEST-1.x cases (security/privacy/engine), meeting the ≥80% coverage gate.
3. Passes the CI gates (TEST-1.6 / SEC-9.2) once they exist.

## Workflow placeholders (undecided)

Not yet defined. Do not assume them; ask or leave as placeholders.

- `[PLACEHOLDER: build / run / test commands]` — no project tooling exists yet.
- `[PLACEHOLDER: branching & PR conventions]` — beyond "new issues use REQUIREMENT_TEMPLATE.md".
- `[PLACEHOLDER: CI pipeline configuration]` — gates required (SEC-9.x, TEST-1.6), not yet implemented.
- `[PLACEHOLDER: directory / module layout]` — no source tree exists yet.
- `[PLACEHOLDER: infrastructure choices]` — owned by ARCHITECTURE.md's `TO BE DECIDED` list.
