---
id: TASK-239
sequence_id: 239
type: task
title: Project-override merge loader for the workflow spec (additive-only)
status: Done
parent: FEAT-209
author: tech-lead
subentities:
- local_id: ST1
  title: Additive-only merge of project override over bundled default
  status: Done
  story: US1
- local_id: ST2
  title: (duplicate — see ST1)
  status: Cancelled
  story: US1
created_at: '2026-06-30T07:49:45Z'
updated_at: '2026-07-06T15:21:05Z'
---
<!-- sq:body -->
## Goal
Make `load_workflow_spec()` capable of layering a **project override** on top of the bundled
default, with **additive-only** semantics. This is the loader core of FEAT-209 — the first task,
everything else depends on it. (AC #1, AC #2; US1.)

## Prereq already satisfied
The `extra="forbid"` hardening Catherine flagged in her comment is **already done** (FEAT-208 /
ADR-232 §5): `WorkflowSpec`, `ItemSpec`, `StatusSpec`, `Lifecycle`, `RefRule` all carry
`ConfigDict(frozen=True, extra="forbid")`, and `_loader.py` routes every sub-model through
`model_validate(...)`. Verify this still holds at the start (a 2-line read) but do NOT redo it.

## What to build
In `src/squads/_workflow/_loader.py`:
- Add a new entry point, e.g. `load_workflow_spec(squad_dir: Path | None = None) -> WorkflowSpec`
  (keep the existing no-arg behaviour — bundled-only — when `squad_dir is None`, so the import-time
  singleton in `__init__.py` is unchanged for now; TASK-240 wires the squad_dir call site).
- When a squad_dir is given, read the project override TOML:
  - from `<squad_dir>/.overrides/workflow.toml` (the override-machinery location — see TASK-244),
    AND/OR the `[workflow.*]` block in the project `.squads.toml`. **Decide one canonical source and
    document it in the body of TASK-244**; the feature body mentions both `.squads.toml` and a
    sibling `.squads.workflow.toml`. Recommend: the `.overrides/workflow.toml` file (consistent with
    templates/roles overrides) is primary; if you also support a `[workflow]` block in `.squads.toml`,
    treat them as mutually exclusive and error if both are present.
- Parse the override the same way `_build_spec` parses the bundled raw dict (reuse `_parse_lifecycle`,
  `_parse_ref_rules`, the `_coerce_*` helpers — route through `model_validate` so `extra="forbid"`
  fires on typo'd keys, which is the whole point Catherine raised).

## Additive-only merge semantics (the crux — AC #2)
Merge the override OVER the bundled default with these rules, raising `SquadsError` (fail-closed) on
any violation:
- **New types/statuses/lifecycles**: accepted (added to the merged maps).
- **Redefining a built-in type's lifecycle / a built-in status / a built-in lifecycle**: REJECTED.
  "Additive-only" means a key that already exists in the bundled default may NOT be shadowed/mutated
  by the override. Detect a collision (same `items` key, same `statuses` key, same `lifecycles` key
  as the bundled default) and raise `SquadsError` with a clear message naming the offending key,
  e.g. "workflow override may not redefine built-in type 'task' (additive-only; you may add new
  types but not change built-ins)".
- New custom types may reference **either** a new custom lifecycle they define **or** an existing
  built-in lifecycle (e.g. `incident` reusing `work`) — that's a *reference*, not a redefinition, so
  it's allowed.
- Build the derived reverse indexes (`prefix_to_type`, `alias_to_type`) over the MERGED set; a new
  type's prefix/folder/alias colliding with a built-in is caught by the existing `_check_item_refs`
  uniqueness checks in `WorkflowSpec._validate` — confirm that path fires (it should, since validate
  runs on the merged spec).

## Acceptance
- A `[workflow.types.incident]` override (new type `incident`, lifecycle `Triage→Mitigating→Resolved`)
  merges cleanly; the resulting `WorkflowSpec.items` contains `incident` plus all built-ins (AC #1).
- An override that redefines `task`'s machine (or any built-in type/status/lifecycle) raises
  `SquadsError` at load time with an actionable message (AC #2).
- A typo'd key in the override TOML raises (extra="forbid" parity — Catherine's flag).
- The no-arg `load_workflow_spec()` still produces the byte-identical bundled spec (AC #7 — the F1
  golden test in tests/test_workflow_spec.py stays green).

## Tests
Service/loader-level: build a tmp squad_dir with an override file, assert the merged spec; assert the
redefine-collision and typo-key cases raise `SquadsError`. Keep the bundled golden-lock test green.

## Ordering
FIRST. TASK-240 (threading) and TASK-241 (index cross-check) build on this loader.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 239 add-subtask "<title>"`; track with `sq task 239 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Additive-only merge of project override over bundled default | US1 |
| ST2 | Cancelled |  | (duplicate — see ST1) | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Additive-only merge of project override over bundled default

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — Project admin can add custom types and statuses via .squads.toml
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Covers the loader core of FEAT-209: `load_workflow_spec(squad_dir)` layers a project override (`.overrides/workflow.toml`, the canonical single source pinned with TASK-244) over the bundled default with ADDITIVE-ONLY semantics. New types/statuses/lifecycles are accepted; redefining any built-in type/status/lifecycle is REJECTED with an actionable `SquadsError` naming the offending key; a new type may REFERENCE a built-in lifecycle (not a redefinition). Derived reverse indexes (prefix_to_type/alias_to_type) are built over the merged set so collisions are caught by the existing uniqueness checks, and the override is parsed through `model_validate` so `extra="forbid"` fires on typo'd keys. The no-arg call stays byte-identical (F1 golden green). (US1)
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — (duplicate — see ST1)

<!-- sq:subtask:ST2:head -->
**Status:** ⚫ Cancelled
**Implements:** US1 — Project admin can add custom types and statuses via .squads.toml
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Cancelled — created as a duplicate of ST1; the additive-only merge is fully covered by ST1. No separate scope. (US1)
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T08:11:45Z] Elias Python:
  - Implemented load_workflow_spec(squad_dir) in _loader.py.
  - Override location: <squad_dir>/.overrides/workflow.toml (mutually exclusive with .squads.toml blocks — recommended canonical source).
  - Additive-only merge: new types/statuses/lifecycles accepted; redefining a built-in raises SquadsError with actionable message. Typo'd keys rejected via extra='forbid'.
  - Added _parse_lifecycle_str/_parse_item_spec_str/_parse_status_spec_str helpers for override parsing (no enum coercion — custom vocab stays as plain strings).
  - validate_against_index(spec, db) added for live-index cross-check (TASK-241 wiring).
- [2026-06-30T08:26:31Z] Mara Tester:
  - AC#1 PASS: load_workflow_spec(squad_dir=...) with a [workflow.types.incident] block merges cleanly. Verified: merged spec contains all bundled types + custom; incident.prefix='INC'; lifecycle='triage' recorded correctly. test_additive_merge_new_type + test_ac1_merged_spec_preserves_all_bundled_types.
  - AC#2 PASS: Redefining a built-in type/status/lifecycle raises SquadsError with message 'may not redefine built-in {kind} {name!r} (additive-only)'. Verified for all three axes. test_redefine_builtin_type_raises / _status_raises / _lifecycle_raises.
  - extra='forbid' parity PASS: a typo'd TOML key in the override raises SquadsError at load time. test_typo_key_in_override_raises.
  - Bypass guards PASS: prefix collision and folder collision with built-in types are both caught by _check_item_refs in the model validator. Added test_folder_collision_with_builtin_raises (folder was not previously tested).
  - Malformed TOML PASS: TOML syntax error in override file raises SquadsError('Malformed workflow override ...'). test_malformed_toml_raises added.
- [2026-06-30T09:19:51Z] Mara Tester:
  - Loader verification: load_workflow_spec(squad_dir) with the worked-example incident spec (Triage/Mitigating/Resolved lifecycle) merges correctly — all bundled types preserved, incident type added with correct prefix/folder/lifecycle. spec.statuses includes Triage/Mitigating/Resolved. validate() passes. AC#1 engine layer PASS. NOTE: the CLI layer is not covered by this task — the defect (sq create incident not registered) is architectural, not in the loader itself.
<!-- sq:discussion:end -->
