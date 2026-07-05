---
id: TASK-215
sequence_id: 215
type: task
title: Build WorkflowSpec pydantic models and author bundled default_workflow.toml
status: Done
parent: FEAT-207
author: tech-lead
subentities:
- local_id: ST1
  title: WorkflowSpec/TypeSpec/StatusSpec/StateMachine models, enum-typed fields
  status: Todo
  story: US1
- local_id: ST2
  title: Author bundled default_workflow.toml encoding today's vocabulary
  status: Todo
  story: US1
created_at: '2026-06-25T14:21:29Z'
updated_at: '2026-06-25T15:17:08Z'
---
<!-- sq:body -->
## Goal

Build the `WorkflowSpec` tree of pyright-strict pydantic v2 value objects per ADR-214 §1, and
author the bundled-default TOML that encodes today's exact workflow vocabulary. This is the data +
shape foundation for FEAT-207 (F1) — **enums intact**: enum-typed fields stay enum-typed; the
spec is a reorganization of today's literals into one object, not a de-typing.

Sequence: **first** task. The loader/rewire (TASK-216) and golden-lock/packaging (TASK-217)
both consume these models and this TOML.

## What to build

- **Models (ADR §1 shape, pyright-strict):**
  - `WorkflowSpec`: `types: dict[ItemType, TypeSpec]`, `statuses: dict[Status, StatusSpec]`,
    `machines: dict[str, StateMachine]`, `subentity_machines: dict[str, StateMachine]`. Derived
    reverse indexes built at load (not stored in TOML): `prefix_to_type`, `alias_to_type`.
  - `TypeSpec`: `prefix: str`, `folder: str`, `machine: str`, `parents: list[ItemType]` (empty =
    unconstrained), `aliases: list[str] = []`. NOTE: capability flags (is_meta, subentity_kind,
    ref_rules) are F2 — NOT in F1.
  - `StatusSpec`: `terminal: bool`, `badge: str | None = None` (only the 9 sub-entity statuses carry
    a badge today).
  - `StateMachine`: `initial: Status`, `transitions: dict[Status, list[Status]]`; `.states` derived
    (initial ∪ all sources ∪ all targets), mirroring `Workflow.states` today.
  - **Enum-typed fields stay enum-typed.** Fields keyed/typed on `ItemType`/`Status` parse from TOML
    *string* values and coerce/validate into the existing enums (`ItemType(...)`/`Status(...)`), so an
    unknown name raises at parse/load. No `str` widening.
- **Bundled TOML** at `src/squads/_workflow/default_workflow.toml` (promote `_workflow.py` into a
  `_workflow/` package with `__init__.py` re-exporting the same public names so import sites are
  unchanged; TOML beside the loader). Ships as package data automatically under
  `[tool.hatch.build.targets.wheel] packages = ["src/squads"]` — same mechanism as templates
  (packaging *verification* is TASK-217). Encode, byte-for-byte vs today:
  - the seven distinct machines (work / adr / review / bug / guide / agent) + the two sub-entity
    machines (subtask/story share subtask; finding has its own), each with `initial` + full
    `transitions`;
  - all statuses with `terminal` flag mirroring today's `TERMINAL` frozenset exactly, plus the
    sub-entity status `badge`s (today's `STATUS_EMOJI`);
  - every type: prefix / folder / machine / parents / aliases — exactly today's `PREFIX_BY_TYPE` /
    `FOLDER_BY_TYPE` / `ALLOWED_PARENTS` / `TYPE_ALIASES`.
  - Priority/severity badges (`PRIORITY_EMOJI`/`SEVERITY_EMOJI`) are NOT workflow vocabulary — out of
    the spec (ADR §1).

## Design constraints (ADR-214)

- §1 shape exactly; enums-intact; no capability flags (F2), no `str` widening, no project overrides.
- The spec must be able to express today's full vocabulary with no new fields beyond what
  `_workflow.py`/`_enums.py` already imply.

## Acceptance

1. `WorkflowSpec`/`TypeSpec`/`StatusSpec`/`StateMachine` exist, pyright-strict-clean, enum-typed
   fields enum-typed (coerce from TOML strings, raise on unknown name).
2. `src/squads/_workflow/default_workflow.toml` exists encoding every current type/prefix/folder/
   machine/terminal/parent/alias/badge; `_workflow.py` promoted to `_workflow/` package with
   re-exported public names (import sites unchanged).
3. `tomllib`-parseable; round-trips into the models without error.
4. pyright/ruff clean. (Equality-with-today is asserted by TASK-217's golden test.)
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 215 add-subtask "<title>"`; track with `sq task 215 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | WorkflowSpec/TypeSpec/StatusSpec/StateMachine models, enum-typed fields | US1 |
| ST2 | Todo |  | Author bundled default_workflow.toml encoding today's vocabulary | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — WorkflowSpec/TypeSpec/StatusSpec/StateMachine models, enum-typed fields

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
### ST2 — Author bundled default_workflow.toml encoding today's vocabulary

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
- [2026-06-25T14:43:51Z] Catherine Manager:
  - NAMING (op-pierre): do NOT use the 'machines' keyword in the workflow spec or default_workflow.toml. Rename the config key + model field — proposed: 'lifecycle(s)' (`[lifecycles.work]`, `TypeSpec.lifecycle`), and 'subentity_lifecycles'; the internal model class can follow (e.g. StatusLifecycle). To be applied/confirmed in the FEAT-207 review pass.
<!-- sq:discussion:end -->
