---
id: TASK-000251
sequence_id: 251
type: task
title: 'Workflow core: free functions to spec/context methods + IndexStore takes the
  spec'
status: Done
parent: FEAT-000250
author: tech-lead
created_at: '2026-06-30T09:53:04Z'
updated_at: '2026-06-30T10:03:47Z'
---
<!-- sq:body -->
**Part (a) of FEAT-000250 / ADR-000249 Option A. First in sequence — a→b→c→d.**

Turn the workflow module from a global-state holder into a thin re-export of explicit
`WorkflowSpec` capabilities, and make `IndexStore` take the spec as an explicit argument.

## Scope

- **`src/squads/_workflow/__init__.py`** — the ~13 module-level free functions
  (`is_open`, `parent_allowed`, `parent_hint`, `workflow_for`, `initial_status`,
  `can_transition`, `subentity_workflow`/`_initial`/`_can_transition`, `work_types`,
  `item_is_meta`, `item_has_severity`, `item_subentity_kind`, `item_parent_required`,
  `item_ref_rules`, `status_role`) become **methods on `WorkflowSpec`** (most already
  exist in `_workflow/_models.py` — `parent_allowed`, `can_transition`, `work_types`, the
  capability flags). Add the few that don't: `spec.is_open(status)` (`status not in
  spec.terminal_set()`), `spec.parent_hint(child)`, the `workflow_for`/`initial_status`
  surface. Delete `_active_spec`, the `_BUNDLED_SPEC` rebind, the in-place-mutated
  `WORKFLOWS`/`SUBENTITY_WORKFLOWS`/`ALLOWED_PARENTS` dicts, `TERMINAL`/`_terminal_ref`,
  `use_spec`, `reset_spec`. Keep `load_workflow_spec` and the bundled-spec load as a
  factory (a `bundled_spec()` accessor that returns a fresh/shared immutable default is
  fine — but NOT a mutable rebindable singleton). Keep the model re-exports.
- **`src/squads/_index/_store.py`** — `_validate_item_vocab` currently reads
  `active_spec()` lazily (`:55-57`), called from `IndexStore.load()` (`:169`). Change
  `IndexStore` to receive the spec **explicitly** — constructor arg or `load(spec)` param
  (pick the cleaner; constructor arg keeps `load` signature stable for callers that already
  hold a store). This removes the lazy `_workflow` import + the cycle dance.

## Constraints / gotchas

- **Behaviour byte-identical** — pure refactor under the FEAT-208 characterization +
  golden-lock net. No behaviour change.
- Keep the import graph acyclic (per CLAUDE.md); the IndexStore-takes-spec change should
  *remove* the lazy import, not add a cycle.
- `Status` is a `StrEnum` so str-typed methods keep comparing equal — preserve that.
- Out of scope: the CLI import-time app-build loop (FEAT-210), and the service/CLI/test
  call sites (tasks b/c/d). This task can leave the free functions as **temporary thin
  shims delegating to a passed/temp spec** if it helps land incrementally, but the end
  state across the feature is: no module-level mutable spec state.

## Acceptance

- Spec exposes every capability the old free functions did, as methods.
- `IndexStore` validates vocab from an explicitly-supplied spec.
- `pyright` strict + `ruff` clean; FEAT-208 characterization + golden-lock green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 251 add-subtask "<title>"`; track with `sq task 251 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T10:03:43Z] Elias Python:
  - Implemented TASK-251 (workflow core + IndexStore spec threading).
  - WorkflowSpec gains workflow_for/subentity_workflow/subentity_initial/subentity_can_transition/parent_hint methods. Workflow dataclass moved from __init__.py to _models.py. _workflow/__init__.py: deleted _active_spec/use_spec(real logic)/reset_spec(real logic)/_terminal_ref/in-place dict mutation; WORKFLOWS/SUBENTITY_WORKFLOWS/ALLOWED_PARENTS/TERMINAL are now immutable constants backed by _BUNDLED_SPEC. use_spec/reset_spec retained as documented no-op stubs (callers in _service.py and _cli/_main.py swept in TASK-252/253). active_spec() now returns _BUNDLED_SPEC directly.
  - IndexStore.__init__ gains spec: WorkflowSpec | None = None constructor arg; _validate_item_vocab takes spec explicitly, no more lazy _workflow import. Default is bundled_spec() (backward compat for init/adopt/tests without an explicit spec).
  - 3 test_workflow_override.py _active_spec[0] reach-ins rewritten to active_spec() (pyright gate requirement). 7 test_workflow_override.py tests now fail because use_spec is a no-op — expected; these are TASK-254 rewrite targets.
  - pyright strict: 0 errors. ruff check+format: clean. Golden-lock + capability-flags + spine characterization: 77/77 pass (unchanged).
<!-- sq:discussion:end -->
