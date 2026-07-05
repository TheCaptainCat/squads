---
id: TASK-242
sequence_id: 242
type: task
title: sq workflow lint — verbose author-facing spec validation surface
status: Done
parent: FEAT-209
author: tech-lead
subentities:
- local_id: ST1
  title: sq workflow lint verbose validate, exit 0/1
  status: Todo
  story: US2
created_at: '2026-06-30T07:49:53Z'
updated_at: '2026-06-30T09:29:55Z'
---
<!-- sq:body -->
## Goal
Add `sq workflow lint` — the friendly, verbose author-facing validation surface. It runs the SAME
validation that `open_service` runs fail-closed (TASK-240/241), but instead of aborting on the
first problem it prints EVERY error and warning with context and a fix hint, and reports "OK" when
clean. (AC #3; US2.)

## Current state
`sq workflow` already exists as a command in `src/squads/_cli/_main.py` (line ~670) — it prints the
team cheatsheet. Today it's a single `@app.command()`. To add a sub-verb `lint`, convert `workflow`
into a small Typer sub-app (a `workflow_app` with the existing cheatsheet as the default/`show` and
`lint` as a new command), OR add `sq workflow lint` as the architecture allows — match how other
groups (e.g. `sq override`, `sq migrate`) are structured. Preserve the bare `sq workflow` cheatsheet
behaviour (it's referenced from the CLI epilog and the `squads` skill).

## What to build
- `sq workflow lint`:
  - Resolve the squad dir, load the MERGED spec in a *collect-all-errors* mode rather than
    fail-on-first. Practically: build the override raw dict, run the parse + merge + pure-spec
    validation + index cross-check (TASK-241), accumulating a list of (level, location, message,
    fix-hint) instead of raising on the first `SquadsError`.
    - This likely means factoring the validation so it can run in two modes: **fail-closed** (raise
      on first, used by open_service) and **collect** (return all findings, used by lint). Coordinate
      with TASK-240/241 so the same checks back both surfaces — do NOT duplicate the rules.
  - Print each finding with the offending config key / TOML location and an actionable fix
    suggestion; group errors vs warnings.
  - Exit code: 0 + "workflow spec OK" on a clean spec; exit 1 when any error is present (US2
    acceptance). Warnings alone should still exit 0 (decide and state in tests).
  - Honour `--json` if the other CLI verbs in the group do (nice-to-have, not required by ACs).

## Acceptance
- `sq workflow lint` on a valid spec (incl. a valid `incident` override) prints OK and exits 0
  (AC #3 / US2).
- On an invalid override (e.g. redefines `task`, references an undeclared lifecycle, omits a status
  still in use) it prints EVERY error with its config key + a fix hint, and exits 1 (US2).
- The bare `sq workflow` cheatsheet still works unchanged.

## Ordering
After TASK-241 (it shares the collect-mode validation). Pairs with TASK-243 (sq check uses the
same validate()); align so both call one validation core.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 242 add-subtask "<title>"`; track with `sq task 242 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | sq workflow lint verbose validate, exit 0/1 | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — sq workflow lint verbose validate, exit 0/1

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US2 — As a project admin, I want sq workflow lint to validate my spec config and report every error clearly before I commit it
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T08:45:38Z] Elias Python:
  - Implemented sq workflow lint (TASK-242). Converted the sq workflow command into a Typer sub-app (workflow_app in _cli/_workflow_cmd.py) with show (backward-compat cheatsheet) and lint sub-commands. lint calls lint_workflow_spec() directly — NOT through open_service — so it can report on specs that would cause open_service to hard-stop.
  - lint_workflow_spec() in _workflow/_loader.py runs all checks in collect-all-errors mode: (1) pure-spec validation via load_workflow_spec() — on SquadsError captures the message as an error finding; (2) live-index cross-check via validate_against_index() on the successfully-loaded spec. Returns list of (level, location, message, fix_hint) tuples; never raises.
  - Exit codes: 0 on clean spec or no override; 1 when any error finding present; warnings-only exits 0. CLI prints a Rich table per error/warning group with location and fix hint columns. Bare sq workflow and sq workflow show both still print the cheatsheet (backward-compat preserved).
- [2026-06-30T09:29:45Z] Elias Python:
  - Fix 1 (AC#3) applied — TASK-242/243 follow-up.
  - Factored `_collect_additive_conflicts(bundled, raw, override_path) -> list[str]` out of `_merge_override`. The new function iterates all keys in the override's lifecycles/statuses/items sections against the bundled built-ins using list comprehensions and returns one message per conflicting key.
  - `_merge_override` raises on `conflicts[0]` (fail-fast, open_service stays fail-closed). `lint_workflow_spec` is rewritten as a three-phase function: (1) read raw TOML via new `_read_raw_override` helper, (2) run `_collect_additive_conflicts` and extend findings with ALL conflicts, (3) if clean, run `load_workflow_spec` for structural errors, then validate_against_index. All three gates (pyright, ruff check, ruff format) clean.
  - Test `test_ac3_additive_conflict_reports_first_only` replaced with `test_ac3_additive_conflict_reports_all_conflicts`: asserts `len(errors) >= 2` when two built-ins are redefined, and checks both 'task' and 'bug' appear in messages. 93/93 pass.
<!-- sq:discussion:end -->
