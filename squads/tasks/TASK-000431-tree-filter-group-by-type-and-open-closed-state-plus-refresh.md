---
id: TASK-431
sequence_id: 431
type: task
title: Tree filter/group by type and open/closed state, plus refresh command
status: Done
parent: FEAT-100
author: tech-lead
assignee: typescript-dev
refs:
- ADR-427:addresses
- TASK-428:depends-on
created_at: '2026-07-16T13:51:29Z'
updated_at: '2026-07-17T07:41:47Z'
---
<!-- sq:body -->
## Goal

Let an operator focus the tree: filter and group by item type and by open/closed state, and refresh the view on demand — so the sidebar shows the work that matters right now.

## Scope

- **Filter/group** the flat/filtered views from `sq list --json` (the surface chosen for filtered/grouped views): filter by item type and by open vs closed (terminal) state; group by type and/or state.
- Commands + UI affordances (view title menu / quick-pick) to set the active filter and grouping.
- A **refresh** command that re-invokes `sq` and rebuilds the view (re-probing discovery on failure per the adapter contract).
- Filtering/grouping is a presentation concern over the adapter output — state derived from `sq list --json` fields, not re-implemented locally beyond grouping/predicate logic.

## Acceptance criteria

- Operator can filter by type and by open/closed state, and group by type and/or state; the view updates accordingly.
- A refresh command re-fetches from `sq` and rebuilds the tree, surfacing failures as notifications.
- Open/closed classification matches the CLI's own terminal/open semantics (derived from `sq list --json` status, not a divergent local list).
- Grouping/filter/predicate logic is unit-tested against committed `sq list --json` fixtures with no live `sq`.
- Passes the strict TS gate (`npm run check`).

## ADR-427 constraints this task must honor

- #2 Consumer contract: filtered/grouped views feed from `sq list --json` via the foundation adapter; MUST NOT read `.claude/` or `.squads.json`.
- #3 Testing: filter/group logic unit-tested against committed fixtures, runnable with no `sq`.

## Implementer note

sq/ticket IDs must not appear in source — name files/tests by behavior (e.g. `filterGroup`, `refreshCommand`). Depends on the foundation task (and shares the tree provider from the US1 task).

Implements FEAT-100 story **US3** — "Filter and group tree by type/state, refresh on demand". Addresses ADR-427.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 431 add-subtask "<title>"`; track with `sq task 431 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-16T18:50:46Z] Ada Typescript:
  - Filter/group logic in src/domain/listView.ts (vscode-free, unit-tested against the committed list.json fixture): excludeReservedTypes, classifyListItems, filterListItems, groupListItems (recursive, ordered by groupBy keys), buildFilteredGroupedView end-to-end.
  - Open/closed classification is derived, not hardcoded: adapter.getListSnapshot (src/sqAdapter.ts) fetches 'sq list --json' twice (once with --all, once without) and diffs the ids -- matches the CLI's own default-hides-closed behaviour with no locally-maintained terminal-status table (statuses are workflow-spec-driven per project, confirmed by reading _workflow.py).
  - Commands + package.json contributions: squads.refreshTree (view/title nav icon), squads.filterByType / squads.filterByState / squads.groupBy (quick-picks, view/title overflow menu), squads.clearFiltersAndGrouping. Setting any filter/grouping switches the same activity-bar tree from hierarchy view to the flat/grouped sq-list-backed view; clearing returns to the hierarchy.
  - Refresh re-invokes sq for whichever view is active and re-probes discovery on a spawn failure (shared SqDiscovery instance with the tree/preview).
  - npm run check clean, npm test 67/67 green (listView.test.ts: filter/group/classify unit tests + an end-to-end pass over the committed fixture). Verification honesty: no live extension host in this environment -- verified via unit tests + npm run check + reading treeDataProvider.ts/commands.ts wiring; extension-host smoke test deferred to CI/manual.
  - @reviewer ready for review.
<!-- sq:discussion:end -->
