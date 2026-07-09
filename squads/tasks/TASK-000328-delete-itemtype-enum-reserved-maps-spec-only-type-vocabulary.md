---
id: TASK-328
sequence_id: 328
type: task
title: Delete ItemType enum + RESERVED maps; spec-only type vocabulary
status: Draft
parent: FEAT-326
author: tech-lead
subentities:
- local_id: ST1
  title: Delete ItemType + RESERVED_*/TYPE_ALIASES; prefix_for is spec-only
  status: Todo
  story: US1
- local_id: ST2
  title: Carry prefix on every Item frontmatter; spec-free id round-trip + load backfill
  status: Todo
  story: US1
- local_id: ST3
  title: Narrow type floor to three is_meta types; META_* constants for meta refs
  status: Todo
  story: US1
created_at: '2026-07-07T14:50:23Z'
updated_at: '2026-07-07T14:52:41Z'
---
<!-- sq:body -->
## Scope

Remove the `ItemType` `StrEnum` and every duplicate hardcoded type-vocabulary
map so the loaded workflow spec is the sole authority on the type axis, and
carry `prefix` on every `Item` so a `.md` file round-trips **without a spec in
hand**. Implements the type-axis half of ADR-322 (US1). This is the primary
bisectable unit for the type axis, minus the playbook/CLI registration (its own
task) and the migration runners (their own task).

## Areas / files

- `_models/_enums.py` — delete `ItemType`, `WORK_TYPES`, `TYPE_ALIASES`, and the
  `.prefix`/`.folder` properties.
- `_models/_vocab.py` — delete `RESERVED_PREFIX` / `RESERVED_FOLDER` /
  `RESERVED_TYPE_BY_PREFIX` / `is_reserved`. `prefix_for(type_str, spec)` returns
  `spec.items[type_str].prefix` for every type; unknown type → `SquadsError`
  (no `type.upper()` guess). Folder resolves from `spec.items[t].folder`.
- `_models/_item.py` — drop the `ItemType` re-export; remove the
  `type not in _RESERVED_PREFIX` guard in `to_frontmatter_dict` so **every** item
  writes a `prefix:` line; remove the reserved-map fallbacks in `Item.id` and
  `from_frontmatter` so the id formats purely from the stored `prefix` string
  (spec-free round-trip; `_models` must not import `_workflow`).
- `_workflow/_loader.py` / `_workflow/_models.py` — drop the `ItemType(...)`
  coercion of TOML keys (keys stay `str`); build the `prefix → type` reverse
  index from `ts.prefix` for all types; narrow `WorkflowSpec._validate`'s type
  completeness floor from "all `ItemType` members" to **only the three `is_meta`
  types** (`role`/`skill`/`operator` present with `is_meta = true`, not
  droppable). Introduce the by-name constants — `META_TYPES` frozenset +
  `META_ROLE`/`META_SKILL`/`META_OPERATOR`.
- `_services/_maintenance.py`, `_roster.py`, `_base.py`,
  `_backends/_claude_code/_backend.py`, `_backends/_agents_md/_backend.py` —
  replace `ItemType.ROLE/SKILL/OPERATOR` with the meta-name constants; resolve
  skill folder/prefix from `spec.items["skill"]`; iterate `spec.items` /
  `spec.work_types()` instead of `for t in ItemType`; `item.type == ItemType.SKILL`
  → `item.type == META_SKILL`.
- Store load boundary — backfill `prefix` onto legacy built-in item files at
  `IndexStore.load()` (the spec-aware post-load pass that already fills
  `id_padding`), tolerant of a missing line.
- Result dataclasses / model fields annotated `ItemType` → `str` (already stored
  as `str` on disk).

## Done criteria

- `grep -rn 'ItemType' src/squads` returns no vocabulary-enum hits (verify any
  identically-named locals by hand).
- `prefix_for` resolves solely from `spec.items[type].prefix`; an unknown type
  raises `SquadsError`.
- Every `Item`, built-in or custom, writes a `prefix:` line; a `.md` round-trips
  through `from_frontmatter`/`to_frontmatter_dict` with no spec loaded.
- The type completeness floor requires only the three `is_meta` types; a spec
  that omits, renames, or re-prefixes a work type loads successfully.
- No-override default squad produces identical IDs and folders.
- `pyright` + `ruff check` + `ruff format --check` clean across the touched files
  (this absorbs the type-axis half of the enum→`str` annotation inversion).

## Sequencing note

The playbook and CLI are the largest `ItemType` consumer cluster; they are
converted to `str`-keyed / `spec.items`-driven registration in the generic
playbook + CLI task. Land that (it interoperates with the surviving `StrEnum`)
before deleting `ItemType` here so this task reaches a green pyright.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 328 add-subtask "<title>"`; track with `sq task 328 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Delete ItemType + RESERVED_*/TYPE_ALIASES; prefix_for is spec-only | US1 |
| ST2 | Todo |  | Carry prefix on every Item frontmatter; spec-free id round-trip + load backfill | US1 |
| ST3 | Todo |  | Narrow type floor to three is_meta types; META_* constants for meta refs | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Delete ItemType + RESERVED_*/TYPE_ALIASES; prefix_for is spec-only

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — Full self-service type vocabulary in spec
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Remove the ItemType StrEnum (with WORK_TYPES/TYPE_ALIASES and the .prefix/.folder properties) and the RESERVED_PREFIX/RESERVED_FOLDER/RESERVED_TYPE_BY_PREFIX/is_reserved maps in _vocab.py. prefix_for(type, spec) becomes spec.items[type].prefix for every type; an unknown type raises SquadsError with no upper()-guess fallback.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Carry prefix on every Item frontmatter; spec-free id round-trip + load backfill

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US1 — Full self-service type vocabulary in spec
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Drop the built-in-only prefix guard in to_frontmatter_dict so every item writes a prefix line; remove the reserved-map fallbacks in Item.id and from_frontmatter so the id formats purely from the stored prefix (no _workflow import). Backfill prefix onto legacy built-in files at the spec-aware IndexStore.load() post-load pass, tolerant of a missing line.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Narrow type floor to three is_meta types; META_* constants for meta refs

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
**Implements:** US1 — Full self-service type vocabulary in spec
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Narrow WorkflowSpec._validate's type completeness floor to the three is_meta types (role/skill/operator, not droppable). Add META_TYPES + META_ROLE/META_SKILL/META_OPERATOR name constants and repoint the meta-type references in _maintenance.py/_roster.py/_base.py/backends at them, resolving skill folder+prefix from spec.items[skill].
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
