---
id: TASK-454
sequence_id: 454
type: task
title: 'VS Code: toolbar & display controls'
status: Done
parent: FEAT-449
author: tech-lead
assignee: typescript-dev
refs:
- ADR-427:addresses
description: 'Client: numeric sort, title-icon toggles, collapse-all, greyed closed
  items (US2/F2-F7)'
created_at: '2026-07-17T13:23:57Z'
updated_at: '2026-07-17T15:30:56Z'
---
<!-- sq:body -->
Story: US2 (toolbar & display controls). Covers REV-448 findings F2, F3, F4, F5, F6, F7. Independent of the webview pivot.

## Scope

- **F2 — numeric id sort (a real defect).** `listView.ts` sorts ids with `a.id.localeCompare(b.id)` — plain lexicographic, so `REV-447` sorts before `REV-48`. Fix with a shared `Intl.Collator(undefined, { numeric: true })` comparator reused *everywhere* ids/sequence numbers are sorted, so it can't recur. This is the item order WITHIN a group (distinct from F1's type-GROUP order).
- **F3 — group-by-type as a title icon.** Move group-by-type from the quick-pick/menu (`squads.groupBy`) to a view-title-bar icon toggle (`contributes.menus` `view/title`, `group: navigation`, command icon).
- **F4 — show-closed toggle.** Add a show-closed view-title icon toggle that includes/excludes terminal items in the current view (replaces switching to a flat state view to see closed items).
- **F5 — drop group-by-open/closed.** Remove the open/closed grouping mode entirely (the state option on `squads.groupBy`). Open/closed becomes the F4 toggle + F7 visual treatment, not a grouping axis. Group-by-type (F3) stays.
- **F6 — collapse-all.** Native path: set `showCollapseAll: true` on the `createTreeView` registration (built-in title-bar icon, no custom command).
- **F7 — greyed closed items.** When closed/terminal items are shown, render them de-emphasized (muted `ThemeColor` — `disabledForeground`/`descriptionForeground` on the `TreeItem`, or `resourceUri` + a `FileDecorationProvider`).

## Requirements

- Open/closed is derived spec-driven from `is_open` (already on tree/list `--json`) — not a hardcoded status list.
- Strict TS gate parity (tsc strict + eslint zero-warnings + prettier).
- Unit-test the shared numeric collator, the closed-item styling, and the toggle state against fixtures.

## Acceptance

- All six behaviors work; no lexicographic id sort remains anywhere (the collator is shared).
- `npm run check` + unit tests green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 454 add-subtask "<title>"`; track with `sq task 454 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T15:24:12Z] Ada Typescript:
  - Implemented F2-F7 in clients/vscode/ (all six).
  - F2: shared domain/idOrder.ts (Intl.Collator numeric), used in listView.ts's leaf sort — no more plain localeCompare on ids.
  - F3: group-by-type moved from the squads.groupBy quick-pick to a view-title icon toggle (squads.toggleGroupByType, package.json 'toggled' context-key binding, $(list-tree)).
  - F4: new squads.toggleShowClosed view-title icon toggle ($(eye)); applies to both the hierarchy tree and the flat/grouped view via getTree/getList --all.
  - F5: dropped group-by-open/closed entirely — GroupKey/state grouping removed from listView.ts and treeDataProvider's ViewState; groupByType is now a plain boolean.
  - F6: createTreeView({ showCollapseAll: true }) replaces registerTreeDataProvider in extension.ts.
  - F7: DisplayNode gained a closed field (derived from is_open in both treeMapping.ts and listView.ts); treeDataProvider dims closed items' icon via ThemeColor('disabledForeground').
  - Removed squads.filterByState (state filtering folded into the show-closed toggle) — not called out explicitly in scope but redundant once F5 landed; flag if you want it kept separately.
  - Gates: npm run check clean, npm test 125/125, npm run test:canary 8/8. New unit coverage: test/idOrder.test.ts (comparator), listView.test.ts/treeMapping.test.ts (closed field, groupByType boolean). The view-title menu wiring (package.json contributes.menus/toggled) and the icon dimming render are CI/manual-only (extension-host smoke + eyeballing), no unit coverage possible for vscode-native rendering.
  - Note: resources/*.svg are showing as modified in the working tree from a concurrent session (looks like TASK-458 icon work in flight) — untouched by me, unrelated to this task.
  - @reviewer please review.
<!-- sq:discussion:end -->
