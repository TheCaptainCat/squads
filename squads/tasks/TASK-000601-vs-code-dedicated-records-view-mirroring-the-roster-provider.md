---
id: TASK-601
sequence_id: 601
type: task
title: 'VS Code: dedicated records view mirroring the roster provider'
status: Done
parent: FEAT-570
author: tech-lead
assignee: typescript-dev
priority: medium
created_at: '2026-07-22T13:00:57Z'
updated_at: '2026-07-23T07:09:24Z'
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

## Role colour
The records view's closed/dim styling is keyed on the item's role (role.settled for closed, role.hidden for dim) joined via the roles catalog, and row colour maps role.color intent -> vscode.ThemeColor with a neutral fallback — replacing the removed is_open/terminal reads. Depends on FEAT-605.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 601 add-subtask "<title>"`; track with `sq task 601 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T17:48:15Z] Ada Typescript:
  - New domain/recordsView.ts::buildRecordsView mirrors metaView.ts but buckets are spec-driven: derived from typeCategory.ts's recordsTypes(categoryMap) + ordered via the type catalog's order field, not a hardcoded 3 (a project's custom records type gets its own bucket with no client change); empty categoryMap => no buckets (can't-tell-yet, distinct from roster's always-3-fixed-buckets).
  - New src/recordsTreeDataProvider.ts mirrors metaTreeDataProvider.ts (one sq list --json --all fetch + type/collections/statuses/roles catalogs). Registered a new 'Records' activity-bar view (package.json viewsContainers/views: squadsRecords) + squads.refreshRecords command (commands.ts registerRecordsCommands); wired in extension.ts (createTreeView, expand/collapse tracking, initial refresh) and the squadWatcher on-disk-change refresh path alongside the work tree and roster views.
  - Reuses displayNode/badgeCatalog/statusRole helpers as directed; closed/hidden/colour styling comes from the same role-catalog join as the work tree and roster (see TASK-600's comment for the ADR-604 migration details this rides on).
  - Gate: tsc/eslint/prettier/vitest all green (386 tests, incl. new test/recordsView.test.ts bucketing tests). Awaiting @op-pierre's dev-host visual pass — check: a new 'Records' section appears in the Squads activity-bar container, alongside Work Items and Roster; it groups decision/guide items (this repo's records types) each under their own bucket, refreshes on file changes, and closed/Accepted-style items render per the new role colours (see TASK-600).
<!-- sq:discussion:end -->
