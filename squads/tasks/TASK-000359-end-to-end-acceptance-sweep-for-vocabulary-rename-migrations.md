---
id: TASK-359
sequence_id: 359
type: task
title: End-to-end acceptance sweep for vocabulary rename migrations
status: Draft
parent: FEAT-281
author: tech-lead
subentities:
- local_id: ST1
  title: End-to-end acceptance of rename-type
  status: Todo
  story: US1
- local_id: ST2
  title: End-to-end acceptance of rename-status
  status: Todo
  story: US2
created_at: '2026-07-09T21:34:36Z'
updated_at: '2026-07-09T21:36:03Z'
---
<!-- sq:body -->
Feature-acceptance sweep proving FEAT-281's criteria end-to-end (separate from the per-task unit/smoke tests in 355-358; this is the honest ground-truth gate — green unit tests are not acceptance).

AC1 (rename-type full): on a squad with a 'ticket' type declared via .overrides/workflow.toml, seed FEAT/TASK/REV items that CARRY sub-entities (stories/subtasks/findings) and non-initial statuses, plus cross-refs and prose @mentions/ID mentions between them; run rename-type task ticket; assert all TASK-… ids -> TICKET-…, the folder moved, every parent/ref/frontmatter and prose mention rewritten, and CRITICALLY that sub-entities AND status are preserved unconditionally (the retype guardrails would have rejected/reset these — the whole point of the feature). Then assert 'sq check' and 'sq repair' are both clean (repair produces no diff).

AC2 (rename-status fail-closed): rename-status to a status NOT in the type's lifecycle fails cleanly with no partial rewrite (assert every item's status unchanged after the failed call). Plus a happy-path rename-status moving all matching items.

AC3 (audit): assert one reflog line per renamed item (op rename-type / rename-status) and a system discussion comment per item, consistent with retype's trail.

AC4 (reserved meta): rename-type / rename-status on role|skill|operator is rejected with a clear error.

AC5 (no schema drift): assert SCHEMA_VERSION is unchanged and _migrations/_registry.py has no new entry (guards the re-baseline #4 decision).

Files owned: tests/ (new acceptance test module, name by behaviour not ticket id per project convention). May add a shared .overrides/workflow.toml fixture under tests/ if 358 didn't. Depends on TASK-358 (full CLI path in place).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 359 add-subtask "<title>"`; track with `sq task 359 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | End-to-end acceptance of rename-type | US1 |
| ST2 | Todo |  | End-to-end acceptance of rename-status | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — End-to-end acceptance of rename-type

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
### ST2 — End-to-end acceptance of rename-status

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
