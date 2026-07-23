---
id: TASK-600
sequence_id: 600
type: task
title: 'VS Code: wire category into type catalog; exclude records from work tree'
status: Done
parent: FEAT-570
author: tech-lead
assignee: typescript-dev
priority: medium
created_at: '2026-07-22T13:00:57Z'
updated_at: '2026-07-23T07:09:24Z'
---
<!-- sq:body -->
Implements FEAT-570 US3 (VS Code plumbing). Wire `category` into the extension's type-catalog consumption and use it to exclude records-category types from the work tree (they move to their own view in TASK-601). Depends on US1 (TASK-595 exposes `category` on `sq workflow types --json`).

## VISUAL — requires operator dev-host visual acceptance
Changes what appears in the work tree. Lands **InReview**; operator (Pierre) verifies on the Windows `code` CLI dev-host (recompile + `--disable-extensions`) before Done. Handoff must say what to check.

## Scope
- `clients/vscode/src/types.ts`: add `readonly category: string` to `SqTypeCatalogEntry`.
- `clients/vscode/src/sqAdapter.ts::isSqTypeCatalogEntry`: extend the shape guard to require `typeof entry.category === 'string'` (the skew-canary reuses this predicate).
- Add a category map built from the catalog, mirroring `domain/typeOrder.ts` / `domain/statusRole.ts` (a `buildCategoryMap(catalog)` + a `NO_CATEGORIES` graceful-fallback). This is the single client-side source of a type's category.
- Work-tree exclusion: today `domain/reservedTypes.ts::isReservedType` excludes only the 3 roster types from the work tree. The work tree must now ALSO exclude `records`-category types (decision/guide/contract + custom), driven by the category map — not by a hardcoded records-name list. Where the catalog hasn't loaded (empty map), degrade gracefully (fall back to today's roster-only exclusion) rather than dropping items.

## Acceptance
- `SqTypeCatalogEntry` carries `category`; the guard rejects an entry missing it.
- The work tree no longer shows decision/guide/contract items (they are handled by TASK-601's view); roster still excluded; custom records excluded by category.
- Extension unit tests for the guard + category map + exclusion.
- Operator dev-host visual sign-off before Done.

## Gates
Extension: its own `npm run` compile + lint + tests (see `clients/vscode`). Repo Python gates unaffected. Leave `sq check` clean.

## Role catalog migration
Alongside the category map, migrate the type/status wiring off the removed is_open/terminal fields: add a roles-catalog fetch + guard (from sq workflow roles --json), and drop the removed SqTypeCatalogEntry.terminal / node is_open shape guards. The category map and the role join are separate client-side sources (type->category, status->role). Depends on FEAT-605.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 600 add-subtask "<title>"`; track with `sq task 600 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T17:48:04Z] Ada Typescript:
  - Migrated off the removed sq --json is_open/terminal fields (ADR-604, release-critical): types.ts drops is_open (SqTreeNode/SqListItem) + terminal (SqStatusCatalogEntry), adds SqRoleCatalogEntry; sqAdapter.ts drops the matching runtime guards, adds isSqRoleCatalogEntry + getRolesCatalog (sq workflow roles --json); domain/statusRole.ts now joins status->role->{settled,hidden,color} via resolveRole/buildRoleCatalogMap (ColorIntent closed-vocab with neutral fallback).
  - DisplayNode.active is gone; closed now = role.settled, new hidden = role.hidden drives the dim/grey styling (decoupled from closed so a settled-but-visible role like Accepted/in_force shows its own colour instead of greying out like finished work), new colorIntent feeds treeItemRendering.ts's THEME_COLOR_BY_EMPHASIS (positive/danger/warning/muted/info -> charts.*/disabledForeground, neutral -> no override). treeMapping/metaView/listView + both tree providers updated to fetch+join the roles catalog.
  - TASK-600 scope: SqTypeCatalogEntry.category added + guard extended; new domain/typeCategory.ts (buildCategoryMap/isRecordsCategory/recordsTypes + NO_CATEGORIES fallback); reservedTypes.ts::isReservedType now also excludes records-category types via the category map (degrades to roster-only exclusion when the map is empty).
  - Gate: tsc --noEmit, eslint --max-warnings 0, prettier --check, vitest all green (386 tests); the extension-host-independent skew canary (npm run test:canary, needs a real sq on PATH) also passes against this repo's live sq. Files: src/types.ts, src/sqAdapter.ts, src/domain/statusRole.ts, src/domain/displayNode.ts, src/domain/typeCategory.ts, src/domain/reservedTypes.ts, src/domain/treeMapping.ts, src/domain/metaView.ts, src/domain/listView.ts, src/treeItemRendering.ts, src/treeDataProvider.ts, src/metaTreeDataProvider.ts + matching test/ files. Awaiting @op-pierre's dev-host visual pass (Windows code CLI, --disable-extensions, recompile first).
<!-- sq:discussion:end -->
