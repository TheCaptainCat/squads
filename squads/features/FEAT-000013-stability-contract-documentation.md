---
id: FEAT-000013
sequence_id: 13
type: feature
title: Stability contract documentation
status: Ready
parent: EPIC-000012
author: product-owner
priority: high
description: docs/stability.md + README tiering the public surfaces and what each
  promises through 1.0
subentities:
- local_id: US1
  title: As a squad user on 0.x, I want a written promise that my items reach 1.0
    via sq migrate up, so that adopting squads before 1.0 is safe
  status: Todo
- local_id: US2
  title: As a script author, I want to know which CLI and --json surfaces are SemVer-stable,
    so that my automation survives upgrades
  status: Todo
- local_id: US3
  title: As an integrator, I want internals (Python import paths, generated .claude/
    files) explicitly marked non-public, so that I don't build on the wrong layer
  status: Todo
created_at: '2026-06-10T12:40:59Z'
updated_at: '2026-06-11T07:54:52Z'
---
<!-- sq:body -->
## Problem

We *behave* as if the `.md` format, the CLI grammar, and the `--json` shapes are stable, but
nothing says so. A user adopting squads today cannot tell which surfaces are safe to build on and
which are internals that may shift without notice. Unstated promises are the worst kind: we are
bound by them anyway, without having chosen their scope.

## Value

A written, tiered contract turns 1.0 from a vibe into a checkable claim. Users know exactly what
they can rely on; we know exactly what we are allowed to change. Every other feature in this epic
gets its acceptance bar from this document.

## Scope

A `docs/stability.md` plus a short README paragraph, tiering the public surfaces:

1. **Durable `.md` format** — the strongest promise: any squad created on any 0.x release reaches
   1.0 intact via `sq migrate up`. The user's items are their data, never hostage to our refactors.
2. **CLI grammar** — commands, arguments and options are SemVer-stable from 1.0.
3. **`--json` output shapes** — stable; additive changes only within a major version.
4. **Python import paths** — explicitly *not* public; the underscore convention is the contract.
5. **Generated `.claude/` files** — regenerable, never migrated; deleting them loses nothing.

This includes settling the **post-1.0 `schema_version` scheme** (today a dotted string tracking
the introducing release) — the decision belongs to the contract, not to a migration PR.

## Acceptance

- `docs/stability.md` exists, covers the five tiers above, and states the migration promise verbatim.
- The README links to it with a one-paragraph summary.
- The post-1.0 `schema_version` scheme is decided and recorded (ADR) and reflected in the doc.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 13 add-story "As a <role>, I want … so that …"`; track with `sq feature 13 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a squad user on 0.x, I want a written promise that my items reach 1.0 via sq migrate up, so that adopting squads before 1.0 is safe |
| US2 | Todo |  | As a script author, I want to know which CLI and --json surfaces are SemVer-stable, so that my automation survives upgrades |
| US3 | Todo |  | As an integrator, I want internals (Python import paths, generated .claude/ files) explicitly marked non-public, so that I don't build on the wrong layer |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a squad user on 0.x, I want a written promise that my items reach 1.0 via sq migrate up, so that adopting squads before 1.0 is safe

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** docs/stability.md states the migration promise verbatim — any squad created on any 0.x release reaches 1.0 intact via `sq migrate up` — and names it the strongest tier.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a script author, I want to know which CLI and --json surfaces are SemVer-stable, so that my automation survives upgrades

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** the doc tiers CLI grammar and --json shapes as SemVer-stable from 1.0, says what 'additive change' means for JSON, and the README paragraph links to it.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As an integrator, I want internals (Python import paths, generated .claude/ files) explicitly marked non-public, so that I don't build on the wrong layer

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
**Acceptance:** Python import paths are documented as not public (underscore convention is the contract) and generated .claude/ files as regenerable-never-migrated; the post-1.0 schema_version scheme is settled and recorded in an ADR linked from the doc.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-11T07:54:11Z] Nina Product:
  - Sequencing note (from the readiness review): this doc is late-binding — it records decisions made by FEAT-000019/027/035/023/024/016/032. Start it early as a living draft, but its Done means 'reflects final decisions': it closes last in the epic.
<!-- sq:discussion:end -->
