---
id: TASK-216
sequence_id: 216
type: task
title: WorkflowSpec loader with fail-closed enum validation; rewire _workflow/_enums
  to source from spec
status: Done
parent: FEAT-207
author: tech-lead
subentities:
- local_id: ST1
  title: load_workflow_spec with importlib.resources/tomllib + fail-closed enum validation
  status: Todo
  story: US1
- local_id: ST2
  title: Rewire _workflow/_enums tables and free functions onto the loaded spec singleton
  status: Todo
  story: US1
created_at: '2026-06-25T14:21:30Z'
updated_at: '2026-06-25T15:17:08Z'
---
<!-- sq:body -->
## Goal

Implement `load_workflow_spec()` (reads the bundled TOML, coerces into enums, runs fail-closed
validation) and rewire `_workflow.py` / `_enums.py` so `WORKFLOWS`/`TERMINAL`/`ALLOWED_PARENTS`/
prefix+folder/alias maps and the free functions are **sourced from the loaded spec** instead of
Python literals — behavior byte-identical, zero call-site churn.

Sequence: **second** — depends on TASK-215 (models + TOML). TASK-217 (golden-lock) gates on
this being behavior-preserving.

## What to build

- **Loader** `load_workflow_spec() -> WorkflowSpec`: read `default_workflow.toml` via
  `importlib.resources` (offline, no-filesystem-assumption package-data access), parse with stdlib
  `tomllib`, coerce every type/status string into its enum, build the derived reverse indexes
  (`prefix_to_type`, `alias_to_type`, `.states`), and run validation (below). A corrupt/invalid
  bundled spec raises `SquadsError` — fail closed (user-facing errors subclass `SquadsError`).
- **Load-time validation** `WorkflowSpec.validate()` (ADR §5, fail-closed):
  1. every `machine.initial` is a declared status;
  2. every transition source and target exists in the status set and in `Status`;
  3. `terminal ⊆ statuses`;
  4. reachability: every state reachable from `initial` (today's machines all reachable → green);
  5. every `TypeSpec.machine` names a declared machine; every `parents` entry is a declared type;
     prefix/folder/alias unique across types;
  6. **enums-intact (F1):** the spec's type set equals `set(ItemType)`; every status used equals its
     enum member — the spec may not omit or invent a name relative to the enums.
  For F1, validation runs only against the bundled default (no project override; `sq workflow lint`
  is F3, not built here).
- **Rewire / shims:** build a module-level default-spec singleton once via `load_workflow_spec()`.
  The existing free functions become **thin shims that read the singleton**: `workflow_for(t)`,
  `initial_status(t)`, `can_transition(t, src, dst)`, `is_open(s)`, `parent_allowed(c, p)`,
  `parent_hint(c)`, and the `TERMINAL` set. Equivalent methods exist on `WorkflowSpec`
  (`spec.can_transition(...)`, `spec.parent_allowed(...)`, `spec.is_open(...)`, `spec.managed_types`,
  etc.) for surfaces that later receive the spec explicitly (F3+ threads a per-`Service` instance);
  in F1 the singleton keeps the free-function interface identical so nothing breaks wholesale.
  `WORKFLOWS`/`ALLOWED_PARENTS`/`PREFIX_BY_TYPE`/`FOLDER_BY_TYPE`/`TYPE_ALIASES`/`STATUS_EMOJI`
  consumers now read from the loaded spec.
- **Leave `parent_hint`'s `if child is ItemType.TASK` branch as-is** — it is a message-text special
  case, not spec vocabulary; reifying it is F2. F1 must not change behavior (ADR §3).
- Keep the import graph acyclic; no `from __future__ import annotations`.

## Design constraints (ADR-214)

- §3 loader/shim design; §5 validation; enums remain the source of names (spec organizes, never
  introduces). No model field widened to `str`; no overrides; no renderer change (`sq workflow` still
  renders the static `workflow.md.j2`).

## Acceptance

1. `load_workflow_spec()` loads + validates the bundled default; invalid spec raises `SquadsError`.
2. Free functions + `TERMINAL` are backed by the loaded singleton; `WorkflowSpec` methods exist for
   explicit-spec surfaces. Call sites unchanged.
3. All existing tests pass unchanged — no behavioral difference for any squad/command; `sq workflow`
   output unchanged. (US1 acceptance.)
4. `uv run pyright && uv run ruff check . && uv run pytest` green. (Golden lock added in TASK-217.)
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 216 add-subtask "<title>"`; track with `sq task 216 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | load_workflow_spec with importlib.resources/tomllib + fail-closed enum validation | US1 |
| ST2 | Todo |  | Rewire _workflow/_enums tables and free functions onto the loaded spec singleton | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — load_workflow_spec with importlib.resources/tomllib + fail-closed enum validation

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a maintainer, I want workflow spec loaded from TOML so behavior is in data not code
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Rewire _workflow/_enums tables and free functions onto the loaded spec singleton

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a maintainer, I want workflow spec loaded from TOML so behavior is in data not code
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
