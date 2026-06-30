---
id: TASK-000258
sequence_id: 258
type: task
title: Spec-aware folder/prefix mapping in _paths for custom types
status: Done
parent: FEAT-000210
author: tech-lead
created_at: '2026-06-30T12:01:05Z'
updated_at: '2026-06-30T12:34:45Z'
---
<!-- sq:body -->
**Slice 2 — spec-aware folder/prefix/ID mapping for custom types.**
Maps to: US1, AC#2.

### Scope
`_paths.py` indexes the hardcoded `_enums` maps directly and will KeyError on a
custom type:
- `SquadPaths.folder_for(item_type)` → `FOLDER_BY_TYPE[item_type]`
- `SquadPaths.squad_relative(item_type, …)` → `FOLDER_BY_TYPE[item_type]`
- `type_for_id(item_id)` → `TYPE_BY_PREFIX[prefix]`
These must consult the active spec (`ItemSpec.folder`, and the spec's
`prefix_to_type` reverse index) for custom types, falling back to / unified with
the built-in maps for reserved types.

Auto-create a custom type's folder if absent. Today `_services/_service.py`
init/adopt iterate `FOLDER_BY_TYPE.values()` to scaffold the type folders — make
that loop iterate the spec's declared folders so a custom type's folder is
created on init/sync.

ID allocation needs NO special path: `SquadsDB.allocate_id` /
`format_id` / `Item.id` already fall back to `PREFIX_BY_TYPE.get(type,
type.upper())` for unknown types (verified) — custom types ride the same global
counter. Add a test that confirms `INC-000001` allocates and round-trips.
Prefix/folder uniqueness is already enforced at spec-load by
`_check_item_refs` (F3) — do not re-implement; just confirm it covers the custom
case.

### The spec handle in _paths
`_paths.resolve()` has no spec today. Decide (smallest viable) how `_paths`
obtains the active spec for the reverse mapping — either thread it from the
caller (Service already owns `self.spec`; `_common.get_active_spec()` is the CLI
handle) or load the override in `resolve`. Prefer threading over a second
filesystem load. Note for the reviewer: keep `_paths` free of import cycles
(it is low in the layering).

### Acceptance
- AC#2: the custom type's folder is auto-created on init/sync; `INC-000001`
  parses correctly via `type_for_id` and round-trips through allocate/format.
- Reserved types unchanged (folders, prefixes, parsing identical).
- A custom-type item file lands in its declared folder and `sq repair` is a
  stable no-op (frontmatter is source of truth — invariant 1).

### Files
- src/squads/_paths.py, src/squads/_services/_service.py (folder scaffold loop),
  tests for allocation/round-trip/folder-creation.

### Dependencies
- Depends on F3 (FEAT-000209, Done) for the spec's `prefix_to_type` index.
- Prerequisite for task 257 (a created `sq incident` item must land on disk).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 258 add-subtask "<title>"`; track with `sq task 258 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T12:34:45Z] Elias Python:
  - Done. folder_for/squad_relative/type_for_id all updated to accept optional spec=; builtins short-circuit through FOLDER_BY_TYPE/TYPE_BY_PREFIX (byte-identical), custom types use spec.items[type].folder / spec.prefix_to_type. WorkflowSpec imported at module top-level in _paths.py — no cycle (checked: _paths→_workflow._models→_models._enums has no back-edges).
  - _iter_item_files() return type widened from Iterator[tuple[ItemType, Path]] to Iterator[tuple[str, Path]] to accommodate custom folder scans. repair/repad/_renumber_plan updated accordingly — callers extract prefix from existing ID strings rather than from the type enum.
  - Folder auto-creation: sync() now scaffolds all spec-declared type folders after the built-in sweep. write_new itself calls mkdir(path.parent) so first-write creates the folder. AC#7 (byte-identical builtins) confirmed by parametrized tests over all ItemType members.
  - 16 tests in tests/test_custom_type_paths.py — all pass. Gate: pyright 0 errors, ruff clean.
<!-- sq:discussion:end -->
