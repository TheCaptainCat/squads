---
id: TASK-454
sequence_id: 454
type: task
title: 'VS Code: toolbar & display controls'
status: Ready
parent: FEAT-449
author: tech-lead
assignee: typescript-dev
refs:
- ADR-427:addresses
description: 'Client: numeric sort, title-icon toggles, collapse-all, greyed closed
  items (US2/F2-F7)'
created_at: '2026-07-17T13:23:57Z'
updated_at: '2026-07-17T13:59:47Z'
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
<!-- sq:discussion:end -->
