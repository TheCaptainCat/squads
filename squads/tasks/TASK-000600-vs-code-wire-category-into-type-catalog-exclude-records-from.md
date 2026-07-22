---
id: TASK-600
sequence_id: 600
type: task
title: 'VS Code: wire category into type catalog; exclude records from work tree'
status: Draft
parent: FEAT-570
author: tech-lead
priority: medium
created_at: '2026-07-22T13:00:57Z'
updated_at: '2026-07-22T13:03:38Z'
---
<!-- sq:body -->
Implements FEAT-570 US3 (VS Code plumbing). Wire `category` into the extension's type-catalog consumption and use it to exclude records-category types from the work tree (they move to their own view in TASK-601). Depends on US1 (TASK-595 exposes `category` on `sq workflow types --json`). Build this before TASK-601/602.

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
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 600 add-subtask "<title>"`; track with `sq task 600 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
