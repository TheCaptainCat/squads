---
id: TASK-345
sequence_id: 345
type: task
title: Relocate badge rendering out of _discussion into a _badges module
status: Cancelled
parent: FEAT-327
author: tech-lead
refs:
- ADR-323
- TASK-342:depends-on
- TASK-343:depends-on
description: 'Pure move: _status_badge/resolve_collection/badge_render out of _discussion.py
  into top-level _badges.py; repoint callers; byte-identical, no golden change'
created_at: '2026-07-09T12:18:37Z'
updated_at: '2026-07-09T12:31:31Z'
---
<!-- sq:body -->
## What this delivers

A pure, byte-identical relocation of the generic badge/presentation helpers out of
`src/squads/_discussion.py` into a focused top-level module (e.g. `src/squads/_badges.py`).
`_discussion.py` is meant for comment/story/subtask prose plus `@mention` extraction; the
badge helpers (`_status_badge`, `resolve_collection`, `badge_render`, and any tightly-related
badge helper) landed there for historical reasons (the old sub-entity-head severity badges)
but are presentation, not discussion. This move leaves `_discussion.py` cohesive.

This is deliberately a **move, not a change** — it must be trivially reviewable as a relocation.

## Scope

- Create the new module and move `_status_badge`, `resolve_collection`, `badge_render` (plus any
  tightly-coupled private badge helper) into it verbatim.
- Repoint every caller: `_discussion`, `_cli/_common`, `_cli/_main`, `_cli/_items`, and the
  head/summary templates via the rendering engine if they reference these.
- No behavior change, no rendering change, no golden change. Keep the import graph acyclic.

## Acceptance

- `_discussion.py` no longer contains any badge-rendering function definitions; a grep confirms
  no badge-render definitions remain there.
- The new module owns them; all callers resolve against it.
- No behavior/golden change (full suite green, no test edits beyond import repoints if any).
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean.

## Sequencing

Dispatch AFTER TASK-342 and TASK-343 land — both are actively editing the `_discussion.py` /
`_cli` badge code. This move must run last, on the settled code, to avoid collision (wired as
depends-on).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 345 add-subtask "<title>"`; track with `sq task 345 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-09T12:31:31Z] Catherine Manager:
  - Reclassified: this is a review finding (module-cohesion — badge rendering misplaced in _discussion), not a feature deliverable. Cancelling the task; it will be recorded as a finding on TASK-342's review and only spawn a fix-task if/when we act on it.
<!-- sq:discussion:end -->
