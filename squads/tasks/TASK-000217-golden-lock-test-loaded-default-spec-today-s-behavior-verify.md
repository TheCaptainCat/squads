---
id: TASK-000217
sequence_id: 217
type: task
title: 'Golden-lock test: loaded default spec == today''s behavior; verify TOML ships
  in wheel'
status: Done
parent: FEAT-000207
author: tech-lead
subentities:
- local_id: ST1
  title: 'Golden-lock test: loaded default spec == frozen snapshot of today'
  status: Todo
  story: US2
- local_id: ST2
  title: 'Build test: default_workflow.toml ships in the wheel'
  status: Todo
  story: US2
created_at: '2026-06-25T14:21:31Z'
updated_at: '2026-06-25T15:17:09Z'
---
<!-- sq:body -->
## Goal

Add the **golden-lock test** — the regression gate for the entire EPIC-000206 — asserting the loaded
default `WorkflowSpec` reproduces today's exact workflow behavior, and verify the bundled TOML ships
in the wheel. This is what proves the externalization (TASK-000215/216) is behavior-preserving and
lets F2+ proceed with confidence.

Sequence: **third** — depends on TASK-000215 (TOML/models) and TASK-000216 (loader). Must remain
green throughout F2–F6.

## What to build

- **Golden-lock test** (ADR §4): build the snapshot directly from today's
  `WORKFLOWS`/`TERMINAL`/`ALLOWED_PARENTS`/`PREFIX_BY_TYPE`/`FOLDER_BY_TYPE`/`TYPE_ALIASES`/
  `STATUS_EMOJI` and assert **structural equality** with the loaded default spec across:
  - the set of `ItemType`s and, per type, its prefix / folder / aliases / parent set;
  - every named machine's `initial` and full `transitions` map (so every legal/illegal transition is
    identical);
  - the `TERMINAL` set, status-by-status;
  - the sub-entity machines per kind;
  - status badges.
  The test must FAIL if any type/status/machine/terminal/parent-rule/badge in the default spec
  differs from the snapshot. CI-enforced; remains green through F2–F6. (US2 acceptance.)
- **Packaging verification:** assert `default_workflow.toml` is included in the built wheel
  (consistent with the templates-are-package-data invariant). Mirror the existing templates-in-wheel
  build test; rely on `[tool.hatch.build.targets.wheel] packages = ["src/squads"]` sweeping non-`.py`
  files — confirm, don't add a per-file include.
- Confirm `sq workflow` output is unchanged (renders the same cheatsheet) as part of the regression
  surface.

## Design constraints (ADR-000214)

- §4 golden-lock contract is the single regression gate for the epic; build the snapshot from today's
  literals (not from the spec) so the spec is checked against an independent source of truth.
- Behavior-preserving: this task adds tests + a packaging check only; no behavior change.

## Acceptance

1. Golden test exists, is CI-enforced, and fails on any drift between the loaded default spec and the
   frozen snapshot of today's `WORKFLOWS`/`TERMINAL`/`ALLOWED_PARENTS`/`PREFIX_BY_TYPE`/
   `FOLDER_BY_TYPE`/`TYPE_ALIASES`/`STATUS_EMOJI`. (FEAT-000207 AC#2, US2.)
2. A build/packaging test confirms `default_workflow.toml` is present in the wheel.
3. `sq workflow` output unchanged (AC#4).
4. `uv run pyright && uv run ruff check . && uv run pytest` all green (AC#5).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 217 add-subtask "<title>"`; track with `sq task 217 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Golden-lock test: loaded default spec == frozen snapshot of today | US2 |
| ST2 | Todo |  | Build test: default_workflow.toml ships in the wheel | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Golden-lock test: loaded default spec == frozen snapshot of today

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US2 — As a maintainer, I want a golden test asserting default spec == today's behavior so regressions are caught immediately
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Build test: default_workflow.toml ships in the wheel

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US2 — As a maintainer, I want a golden test asserting default spec == today's behavior so regressions are caught immediately
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-25T14:47:16Z] Elias Python:
  - @manager TASK-215/216/217 complete — FEAT-000207 F1 implemented and all gates green.
  - Files added/changed:
  -   src/squads/_workflow/_models.py  — WorkflowSpec pydantic v2 frozen models (StateMachine, TypeSpec, StatusSpec, WorkflowSpec) with model_validator fail-closed validation
  -   src/squads/_workflow/_loader.py  — load_workflow_spec() via importlib.resources + tomllib; coerces string keys to ItemType/Status enums; raises SquadsError on any violation
  -   src/squads/_workflow/default_workflow.toml  — bundled spec: 6 machines, 3 subentity machines, 24 statuses (9 badges), 10 types with prefix/folder/machine/parents/aliases
  -   src/squads/_workflow/__init__.py  — replaces _workflow.py; module-level singleton _DEFAULT_SPEC; backward-compat Workflow dataclass shim; all free functions; __all__
  -   src/squads/_services/_retype.py  — fixed identity check (is → ==) so types sharing the same machine (e.g. epic/feature both on 'work') correctly carry status
  -   tests/test_workflow_spec.py  — 15 tests: golden-lock (type set, prefixes/folders, aliases, parents, machine assignments, transitions, Workflow shim, terminal set, badges, subentity machines), importlib access, wheel packaging, sq workflow CLI
  - Gates: uv run pytest -q → exit 0 (all tests pass, 1 skip); uv run pyright → 0 errors; uv run ruff check . → all clean; uv run ruff format --check . → 128 files already formatted. Tasks 215/216/217 marked Done.
<!-- sq:discussion:end -->
