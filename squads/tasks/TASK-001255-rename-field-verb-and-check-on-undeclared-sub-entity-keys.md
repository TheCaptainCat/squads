---
id: TASK-1255
sequence_id: 1255
type: task
title: rename-field verb and check on undeclared sub-entity keys
status: Draft
parent: FEAT-1249
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-1250:implements
- MILE-1241:targets
- TASK-1254:depends-on
description: sq migrate rename-field and frontmatter_key_undeclared on sub-entity
  entries
subentities:
- local_id: ST1
  title: Undeclared keys on sub-entity entries in check
  status: Todo
  story: US8
- local_id: ST2
  title: The rename-field verb
  status: Todo
  story: US8
created_at: '2026-10-29T19:55:10Z'
updated_at: '2026-10-29T19:56:26Z'
---
<!-- sq:body -->
## Goal

A value left under a renamed or dropped field code is kept, reported by `sq check`, and moved by one verb (ADR-1250 section 6; FEAT-1249 US8).

## Scope

- `frontmatter_key_undeclared` scans sub-entity entries as well as items, and its finding names `sq migrate rename-field`.
- `sq migrate rename-field <old> <new>`, beside `rename-type` and `rename-status`: an operation, its binding, a service handler and the Typer command; one transaction over items and sub-entities.

## Expected files

- `src/squads/_services/_validators.py` (the undeclared-key rule)
- `src/squads/_cli/_migrate.py`, `src/squads/_api/_ops.py`, `src/squads/_api/_dto/` (the request and response), `src/squads/_services/_bindings.py`, the rename service module (`_services/_rename.py` or `_maintenance.py`, whichever holds `rename-status`)
- `tests/cli/test_migrate.py`, `tests/check/` (the rule's breach case)

## Runs beside

The guards-and-suite task. That task parametrizes `tests/cli` over both squads and merges last, rebasing over this task's new `test_migrate.py` and `tests/check` cases. Source files are not shared.

## Tests (about 6 new)

Listed per subtask, on the override test squad.

## Size

M.

## Working rules

- Work in your own git worktree off `origin/release/0.19`. At most two Python developers run in parallel on this feature; the "Runs beside" line says who shares files with you.
- Gates before handback: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`, `uv run --all-extras ruff format --check .`, the tests your diff selects plus the floor (`tests/meta`, `tests/cli`, `tests/check` for any change under `_specs/`, `_rendering/templates/` or `_cli/`), and `sq check` clean for the items you touched. The main loop runs the full suite.
- Tests follow ADR-1172 as amended: CLI surface cases with `@pytest.mark.covers(...)`, one case per behaviour plus its boundary refusals, no unit tests on internal functions, no shape tables. A check rule gets its `@pytest.mark.breaches(...)` case. Once the override test squad exists, the override-side cases run on it rather than on a squad built inline. Falsify each new test once (break the code, see it red, restore) and say so in the handback.
- Any edit under `src/squads/_rendering/templates/` runs `python scripts/gen_template_manifest.py` in the same change (the working version is 0.19.0, so the regen writes the 0.19.0 key).
- Comments and docstrings: one or two sentences, present tense, no ticket IDs, release versions or history. No ticket IDs or process words in test names.
- No bundled type, kind, field, collection, status or alias literal in code outside `_specs/` and `_migrations/`: derive it from the active spec (ADR-1250 section 1).
- CHANGELOG and adopter docs are the tech writer's. Report every adopter-visible change (what an adopter now does or sees differently, and why) in your handback comment; do not edit `CHANGELOG.md` or `docs/`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1255 add-subtask "<title>"`; track with `sq task 1255 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Undeclared keys on sub-entity entries in check

<!-- sq:subtask:ST1:body -->
A stored key the active spec does not declare on that type or kind is kept, never a load refusal. `sq check` reports it under `frontmatter_key_undeclared` on items and on sub-entity entries, and the finding names `sq migrate rename-field`.

Tests (1): a breach case on a sub-entity entry carrying an undeclared key (`@pytest.mark.breaches`), asserting the finding names the entry and the verb.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — The rename-field verb

<!-- sq:subtask:ST2:body -->
`sq migrate rename-field <old> <new>` moves every stored value from key `<old>` to `<new>` on items and sub-entity entries, in one transaction. It refuses, exit 1 with nothing written, when an entry's type or kind does not declare `<new>`, when an entry already holds `<new>`, or when a moved value is not a badge of `<new>`'s collection; the refusal names the entry. A kind rename needs no data move: after a rename that keeps `local_prefix`, `sq check` is clean and mappings still resolve.

Tests (5): a move over an item and a sub-entity entry leaves `sq check` clean; the three refusals, each leaving every file byte-identical; a kind renamed in the override with the same `local_prefix` leaves `sq check` clean and `show` resolving the mapping.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
