---
id: FEAT-281
sequence_id: 281
type: feature
title: Vocabulary rename migrations (sq migrate rename-type/status)
status: Draft
parent: EPIC-280
author: product-owner
refs:
- FEAT-210:depends-on
- FEAT-211:depends-on
- FEAT-326:depends-on
subentities:
- local_id: US1
  title: As a project admin, I want sq migrate rename-type to safely rename a built-in
    type across my whole squad
  status: Todo
- local_id: US2
  title: As a project admin, I want sq migrate rename-status to safely rename a status
    across all items of a type
  status: Todo
created_at: '2026-07-02T09:25:53Z'
updated_at: '2026-07-07T14:40:01Z'
---
<!-- sq:body -->
## What this delivers

Today, renaming a built-in type or status (e.g. `task` → `ticket` project-wide, or a status rename) is not supported — additive-only overrides intentionally forbid silent mutation of built-in vocabulary. This feature exposes safe, audited renames built on the existing `retype` machinery (which already rewrites IDs, parent links, and prose mentions atomically), so a project can evolve its vocabulary without manual file surgery or broken refs.

## Scope

- `sq migrate rename-type <old-type> <new-type>`: rewrites all IDs, parent links, folder layout, and prose `@mentions` of the old type atomically, reusing `_services/_retype.py`. The additive-only override constraint is relaxed for this migration path only. Requires a schema bump.
- `sq migrate rename-status <type> <old-status> <new-status>`: rewrites all items of the given type from the old status to the new status. Fails closed if the new status is not in the spec's vocabulary for that type.
- Both are `sq migrate`-style audited data-rewrite events (runbook + `manual` string in `_migrations/_registry.py`), not config edits — they are logged, not silent.

## Non-goals

- Renaming squads' own meta-types (`skill`, `role`, `operator`) — these carry special reserved-vocabulary semantics (ADR-266); rename support for meta-types is explicitly out of scope.

## Dependencies

Requires F4 (FEAT-210, Done) — rename-type operates on custom-type folders/prefixes established there. Requires F5 (FEAT-211, InProgress) for `rename-status` — safe status rename needs the spec-derived open/terminal classification and status vocabulary validation F5 delivers. Do not start until F5 lands.

## Acceptance criteria

1. `sq migrate rename-type task ticket` rewrites all TASK-… IDs to TICKET-…, moves the folder, updates refs and parent links atomically; `sq check` and `sq repair` are clean after.
2. `sq migrate rename-status <type> <old> <new>` transitions all items of that type from old to new status; fails cleanly (no partial rewrite) if the new status is not valid for the type.
3. Both operations are logged as audited migration events with a `manual` runbook entry, consistent with the `sq migrate` changelog convention.
4. Renaming a reserved meta-type (`skill`/`role`/`operator`) is rejected with a clear error.
5. The F1 golden test and all existing tests remain green.
6. A schema bump accompanies the change, with the migration registered in `_migrations/_registry.py`.

## Provenance

Split from the former FEAT-212 ("Custom sub-entity kinds + vocabulary rename migrations") per ADR-274 (Accepted) — this feature is the rename-migrations half; the custom-sub-entity-kinds half stayed on FEAT-212, re-parented to this feature's sibling epic EPIC-280.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 281 add-story "As a <role>, I want … so that …"`; track with `sq feature 281 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a project admin, I want sq migrate rename-type to safely rename a built-in type across my whole squad |
| US2 | Todo |  | As a project admin, I want sq migrate rename-status to safely rename a status across all items of a type |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a project admin, I want sq migrate rename-type to safely rename a built-in type across my whole squad

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a project admin, I want `sq migrate rename-type <old> <new>` to safely rename a type across my entire squad — rewriting all IDs, folders, refs, and prose mentions atomically — so that I can evolve my team's vocabulary without manual file surgery or broken refs.

**Acceptance:** `sq migrate rename-type task ticket` rewrites all TASK-… IDs to TICKET-…, moves the folder, updates all parent/ref links and frontmatter; `sq check` and `sq repair` are clean after; the operation is logged as an audited migration event.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a project admin, I want sq migrate rename-status to safely rename a status across all items of a type

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a project admin, I want `sq migrate rename-status <type> <old> <new>` to rewrite all items of a given type from an old status to a new one, so that I can evolve my status vocabulary without leaving items in a stale or invalid state.

**Acceptance:** the migration transitions all matching items atomically; it fails cleanly with no partial rewrite if the new status is not valid for the type; the operation is logged as an audited migration event.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
