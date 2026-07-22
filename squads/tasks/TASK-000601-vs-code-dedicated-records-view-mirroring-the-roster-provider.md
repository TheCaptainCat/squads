---
id: TASK-601
sequence_id: 601
type: task
title: 'VS Code: dedicated records view mirroring the roster provider'
status: Draft
parent: FEAT-570
author: tech-lead
priority: medium
created_at: '2026-07-22T13:00:57Z'
updated_at: '2026-07-22T13:03:39Z'
---
<!-- sq:body -->
Implements FEAT-570 US3 (VS Code records view). Add a dedicated records view/provider, mirroring how the roster already has its own provider separate from the work tree. Depends on TASK-600 (category plumbing + work-tree exclusion).

## VISUAL — requires operator dev-host visual acceptance
New activity-bar view. Lands **InReview**; operator (Pierre) verifies on the Windows `code` CLI dev-host before Done. Handoff must describe what the new view should show.

## Scope
- New domain builder mirroring `clients/vscode/src/domain/metaView.ts` (`buildMetaView` -> `buildRecordsView`): bucket `sq list --json` rows whose type is `records`-category (via TASK-600's category map) into per-type groups, numeric-id order, each group present. Unlike roster's fixed 3 buckets, records buckets are the declared records types (spec-driven), so derive them from the catalog, not a hardcoded list.
- New tree data provider mirroring `metaTreeDataProvider.ts`; register the view in `package.json` (viewsContainers/views) and wire it in `extension.ts` + `commands.ts` + the `squadWatcher` refresh path, exactly as the roster view is wired.
- Reuse `displayNode`/`badgeCatalog`/`statusRole` helpers; honor category-aware visibility for the "closed" styling consistent with US1.

## Acceptance
- A Records view appears with decision/guide/contract (+ custom records) grouped by type; refreshes on file changes.
- Extension unit test for `buildRecordsView` bucketing.
- Operator dev-host visual sign-off before Done.

## Gates
Extension: its own compile + lint + tests. Leave `sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 601 add-subtask "<title>"`; track with `sq task 601 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
