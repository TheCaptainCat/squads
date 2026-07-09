---
id: TASK-358
sequence_id: 358
type: task
title: Wire rename-type/rename-status sq migrate CLI commands
status: Draft
parent: FEAT-281
author: tech-lead
subentities:
- local_id: ST1
  title: sq migrate rename-type CLI command
  status: Todo
  story: US1
- local_id: ST2
  title: sq migrate rename-status CLI command
  status: Todo
  story: US2
created_at: '2026-07-09T21:34:35Z'
updated_at: '2026-07-09T21:36:02Z'
---
<!-- sq:body -->
Implements US1+US2 CLI surface. Add two sq migrate sub-commands in src/squads/_cli/_migrate.py, siblings of 'repad' (NOT registry migrations): 'sq migrate rename-type <old-type> <new-type>' and 'sq migrate rename-status <type> <old-status> <new-status>'.

Follow the repad command shape exactly: @migrate_app.command + @common.command (async), get_service(), call svc.rename_type(...) / svc.rename_status(...), print a green summary from the returned RenameResult (count renamed, e.g. 'TASK -> TICKET, N item(s) renamed; index rebuilt'), and advise 'run sq check' after. Validation/refusal errors are raised as SquadsError by the service and rendered cleanly (exit 1) by the existing handler.

These are on-demand, project-invoked data rewrites (re-baseline #4) — do NOT touch SCHEMA_VERSION and do NOT add an entry to _migrations/_registry.py; nothing to add to 'sq migrate help'/chlog (repad is the precedent: a migrate sub-command absent from the changelog). Extend the module docstring's command list at the top of _migrate.py to mention the two new commands.

CLI smoke tests: rename-type happy path (with a target type declared via a test .overrides/workflow.toml fixture), rename-status happy path, and the reserved-meta / invalid-new-status rejection paths surfacing a clean exit 1. Watch the FORCE_COLOR harness gotcha — assert on plain text, conftest strips ANSI.

Files owned: src/squads/_cli/_migrate.py, tests/test_cli_migrate.py (or the existing migrate CLI test module — extend it). Depends on TASK-356 and TASK-357 (both service methods must exist).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 358 add-subtask "<title>"`; track with `sq task 358 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | sq migrate rename-type CLI command | US1 |
| ST2 | Todo |  | sq migrate rename-status CLI command | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — sq migrate rename-type CLI command

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a project admin, I want sq migrate rename-type to safely rename a built-in type across my whole squad
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — sq migrate rename-status CLI command

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US2 — As a project admin, I want sq migrate rename-status to safely rename a status across all items of a type
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
<!-- sq:discussion:end -->
