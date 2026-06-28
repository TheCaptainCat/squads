---
id: FEAT-000176
sequence_id: 176
type: feature
title: 'Parameterized item-file storage: layout and identity'
status: Draft
parent: EPIC-000031
author: product-owner
refs:
- FEAT-000177
- FEAT-000032
description: Config knobs for ID prefix and file layout (flat vs per-type subfolders)
  behind the local item-file store
subentities:
- local_id: US1
  title: Single configurable global ID/folder prefix
  status: Todo
- local_id: US2
  title: Flat single-directory file layout
  status: Todo
created_at: '2026-06-23T12:32:58Z'
updated_at: '2026-06-26T09:38:53Z'
---
<!-- sq:body -->
## Problem

Today's local item-file management hard-codes two decisions that should be configurable: (1) each item type gets its own ID prefix (FEAT-, TASK-, BUG-, …) which drives both the formatted ID *and* the prefix→folder mapping; (2) item files are sorted into per-type subfolders (features/, tasks/, …) under the squad directory. Neither decision is load-bearing for correctness — they are conventions that some teams will want to override.

## Value

Letting teams choose a single global prefix (e.g. a project code) and a flat layout reduces friction for squads that don't want to mirror the built-in taxonomy in their filesystem. This feature is the lighter half of the item-file parameterization work — it touches ID formatting and path resolution, not serialization — and could ship independently of FEAT-000177 (the format swap).

## Scope

- A storage abstraction layer behind today's local file management: path resolution, ID prefix/folder mapping. Configurable through `.squads.toml`.

- **Config knob 1 — Custom global prefix:** one configurable prefix string that applies to all item types, replacing the built-in per-type prefix table.

  **OPEN QUESTION (do not resolve here):** does the configurable prefix change the ID prefix, the folder prefix, or both? Today the per-type prefix drives both the formatted ID (FEAT-000001) and the prefix→folder map (features/). Decoupling these may be necessary — this needs an explicit design decision before implementation.

- **Config knob 2 — Flat layout:** all item files land in a single directory instead of per-type subfolders. The squad dir structure becomes flat when this is on.

## Out of scope

Serialization format changes (markdown → JSON/XML). Those are tracked in FEAT-000177 and require an architect ADR first.

## Acceptance

- A team can configure a custom global prefix in `.squads.toml`; `sq create`, `sq list`, and all ID-bearing output reflect it.

- A team can configure flat layout in `.squads.toml`; all item files land in the squad root, not per-type subfolders.

- The open question on prefix scope (ID vs folder vs both) is answered in a design decision before implementation begins.

- Existing squads with default settings are unaffected (no migration required for the default configuration).

- `sq check` and `sq repair` work correctly under both layouts.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 176 add-story "As a <role>, I want … so that …"`; track with `sq feature 176 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Single configurable global ID/folder prefix |
| US2 | Todo |  | Flat single-directory file layout |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Single configurable global ID/folder prefix

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a team, I want one configurable ID/folder prefix for all item types so that our squad reflects our project code instead of the built-in type taxonomy.

**Acceptance:**

- A `prefix` key in `.squads.toml` sets one string that replaces all per-type prefixes.
- All sq commands that produce IDs — create, show, list, tree, ref, comment — use the configured prefix.
- OPEN QUESTION: does the prefix apply to the formatted ID only, the folder name only, or both? The built-in behavior couples them (FEAT- → features/); a custom prefix may need them decoupled. This must be answered in a design decision before implementation.
- The default behavior (per-type prefixes) is unchanged when the key is absent.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Flat single-directory file layout

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a team, I want all item files in one flat directory so that our squad doesn't fragment files across per-type subfolders.

**Acceptance:**

- A `layout = flat` key in `.squads.toml` places all item files in the squad root directory (no subfolders).
- `sq create`, file resolution in `_paths.py`, and all path-bearing output reflect the flat layout.
- `sq repair` and `sq check` work correctly in flat mode.
- The default per-type subfolder layout is unchanged when the key is absent.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-23T12:59:49Z] Robert Architect:
  - @product-owner ADR-000179 now exists addressing the open prefix-scope question: recommends the global prefix change the ID prefix only, with folder layout as a separate orthogonal knob (nested|flat), both plugging into a shared ItemStore locator seam. It cross-references ADR-000180 (FEAT-000177), which shares that seam. Left Proposed for review — not Accepted, no tasks created.
<!-- sq:discussion:end -->
