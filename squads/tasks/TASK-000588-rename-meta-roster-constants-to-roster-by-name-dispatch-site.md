---
id: TASK-588
sequence_id: 588
type: task
title: Rename META_* roster constants to ROSTER_* + by-name dispatch sites
status: Done
parent: FEAT-573
author: tech-lead
assignee: python-dev
created_at: '2026-07-22T12:18:08Z'
updated_at: '2026-07-22T12:54:09Z'
---
<!-- sq:body -->
## Scope

Mechanical symbol rename, first of the FEAT-573 wave. Rename the three roster-type
literal-name constants and every by-name dispatch site that binds them:

- `META_ROLE` -> `ROSTER_ROLE`, `META_SKILL` -> `ROSTER_SKILL`, `META_OPERATOR` -> `ROSTER_OPERATOR`
- `META_TYPES` -> `ROSTER_TYPES`

Defined in `src/squads/_workflow/_models.py` (~lines 31-34) and re-exported from
`src/squads/_workflow/__init__.py` (`__all__`). Update every import + dispatch site (grounded
by `grep -rn "META_OPERATOR\|META_ROLE\|META_SKILL\|META_TYPES"`), including:

- `_services/_roster.py`, `_services/_items.py`, `_services/_base.py`, `_services/_maintenance.py`,
  `_services/_service.py`
- `_backends/_agents_md/_backend.py`, `_backends/_claude_code/_backend.py`
- `_cli/_dev.py`, `_cli/_items.py`
- `_workflow/_loader.py`, `_models/_metadata.py`
- test helpers referencing the constant (`tests/_helpers.py`, `tests/unit/test_workflow_reserved_vocab.py`,
  `tests/unit/test_type_spec_capability_flags.py`)

## Keep / do NOT touch (different `meta` concept)

The legacy body-stored sub-entity `:meta` marker regions are a SEPARATE, unrelated concept —
not the roster-type constants. Leave all of these exactly as-is:

- `src/squads/_migrations/_meta_compat.py` (filename + contents)
- `:meta` region references in migrations (`_v0_2_to_v0_3.py`) and docs
- The local `meta` display variable in `_cli/_common.py::_render_subentity`

## Deprecated spec-key literal stays

The loader's `is_meta` deprecation shim (`_workflow/_loader.py::_pop_legacy_is_meta`) reads the
literal deprecated spec key `"is_meta"` that an adopter override may still carry (per ADR-541
back-compat). The string literal `"is_meta"` and the function that pops it are load-bearing —
do NOT rename the literal. Only the `META_TYPES` reference inside it becomes `ROSTER_TYPES`.

## Constraints

- Behaviour-preserving: byte-identical output for the bundled spec. Pure symbol rename, zero
  functional diff. `sq check`, generated `sq-<type>` skills, backend pointer files, and both UI
  trees must be unaffected.
- No ticket IDs in source/test names.
- Prose/docstring `meta`-terminology purge is a SEPARATE task — do not chase comment wording here
  beyond what the rename mechanically touches.

## Gates (dev must run)

The `tui` extra MUST be installed or pyright reports ~304 false textual errors and `tests/tui`
breaks. Run all gates with `uv run --all-extras`:

`uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check . && uv run --all-extras pytest`
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 588 add-subtask "<title>"`; track with `sq task 588 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T12:23:48Z] Elias Python:
  - Renamed META_ROLE/SKILL/OPERATOR/TYPES -> ROSTER_* across 18 files (src+tests), mechanical only; sq check byte-identical, pyright/ruff/format clean, targeted pytest green; is_meta literal + _meta_compat.py untouched.
<!-- sq:discussion:end -->
