---
id: FEAT-537
sequence_id: 537
type: feature
title: VS Code full-text search (QuickPick)
status: Done
author: product-owner
priority: medium
description: Read-only QuickPick over sq search --json in the VS Code extension; submit/debounced,
  opens the hit in the existing reader.
subentities:
- local_id: US1
  title: Open the search QuickPick and enter a query
  status: Todo
- local_id: US2
  title: Narrow results by item type and/or status
  status: Todo
- local_id: US3
  title: Select a result to open it in the reader
  status: Todo
- local_id: US4
  title: Empty-query, no-results, and busy states
  status: Todo
created_at: '2026-07-21T14:17:03Z'
updated_at: '2026-07-22T09:10:15Z'
---
<!-- sq:body -->
## Capability

Full-text search in the VS Code extension, surfaced as a **QuickPick** (the native
Ctrl+P-style palette). It is a read-only consumer of the existing `sq search <text>
--type --status --json` contract — the same `svc.search` engine the TUI search page
(FEAT-526) uses — so no new search capability, index, ranking, or searched field is
introduced on either side.

The extension already shells out to `sq --json` through `sqAdapter.ts` and renders
items via its item preview/reader. This feature reuses both: a new adapter method +
shape guard for the search JSON, and the existing reader to open a selected hit.

## Latency posture

`sq` pays a per-invocation cold-start (~0.6s interpreter+import, ~1s for a real
search), so the QuickPick **does not search per keystroke**. It fires on submit /
short debounce with a busy indicator — one process per query, not one per keystroke.
This is deliberate and forward-compatible: when the planned warm `sq` daemon lands,
the same submit path drops to fast with no rework here.

## Acceptance

- A command / keybinding opens the search QuickPick from anywhere in the extension.
- Entering a query and submitting (Enter or a short debounce, not per-keystroke)
  lists matching items, each showing id, type, title, and the matched snippet(s)
  `sq search --json` returned.
- Results can be narrowed by item type and/or status, AND-composed with the text the
  same way `sq search`'s `--type`/`--status` compose.
- A search in flight shows a busy indicator; the UI never blocks silently.
- An empty query shows a clean "type to search" state; a query with zero matches
  shows a clean "no results" state — neither is an error or a traceback.
- Selecting a result opens that item in the extension's existing reader/preview.
- Dismissing the QuickPick returns cleanly to the prior editor/view state.

## Non-goals (this feature)

- No new search capability beyond `sq search --json` (no new index, ranking, or
  fields searched, and no re-matching corpus text in the extension).
- No live per-keystroke querying (revisit only once the warm daemon exists).
- No mutation of any item from the search surface (no transition, comment, assign).
- No saved/recent searches.
- The `sq` daemon itself is out of scope — planned separately; this feature works on
  today's cold-start `sq` and simply benefits for free when the daemon arrives.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 537 add-story "As a <role>, I want … so that …"`; track with `sq feature 537 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Open the search QuickPick and enter a query |
| US2 | Todo |  | Narrow results by item type and/or status |
| US3 | Todo |  | Select a result to open it in the reader |
| US4 | Todo |  | Empty-query, no-results, and busy states |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Open the search QuickPick and enter a query

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a squads user in VS Code, I want to open a search palette and type a query, so I can find items by content without walking the tree.

**Acceptance:** A command (and keybinding) opens a QuickPick from anywhere. Typing a query and submitting (Enter or a short debounce — not per-keystroke) runs one `sq search <text> --json` and lists each hit's id, type, title, and returned snippet(s). A search in flight shows a busy indicator.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Narrow results by item type and/or status

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a user with a large board, I want to narrow a search by item type and/or status, so results stay relevant.

**Acceptance:** The QuickPick exposes type and status narrowing that maps to `sq search`'s `--type`/`--status`, AND-composed with the query text exactly as the CLI composes them. No client-side re-matching — the filters are passed through to `sq search`.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Select a result to open it in the reader

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As a user, I want to pick a result and land in the item, so search is a jumping-off point, not a dead end.

**Acceptance:** Selecting a result opens that item in the extension's existing reader/preview surface. Dismissing the QuickPick without selecting returns cleanly to the prior editor/view state.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Empty-query, no-results, and busy states

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
As a user, I want empty, no-match, and loading states to be clean, so the feature never looks broken.

**Acceptance:** An empty query shows a 'type to search' state; a zero-match query shows a clean 'no results' state; a query in flight shows a busy indicator. None of these render an error or a traceback.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T23:55:02Z] Mara Tester:
  - 2026-07-22 QA headless verification (dev-host visual check still pending):
  - Contract check PASS — real sq search --json (throwaway squad) matches isSqSearchHit exactly: id/title/type/status all strings, hits[] all {region,location,snippet} strings; --type/--status compose AND with query; zero-match query returns [] on exit 0.
  - package.json registers squads.search (command + ctrl+alt+s/cmd+alt+s keybinding).
  - npx vitest run: 360/360 pass; sqAdapter.test.ts covers getSearch/isSqSearchHit, searchFilterArgs.test.ts covers --type/--status pass-through, searchRunner.test.ts covers debounce/last-query-wins, searchAccept.test.ts covers decideAccept.
  - Filed BUG-563 (medium) for REV-562 F1's root cause: reproduced a body-only hit whose snippet truncates the matched term before column 160, confirming the server-side windowing defect independent of the client. Refs FEAT-537 and REV-562.
  - Recommend: TASK-558/559/560/561 -> Done, FEAT-537 -> InReview for operator visual acceptance in the dev host (QuickPick UI itself is out of headless-verification scope).
- [2026-07-22T09:10:15Z] Pierre Chat:
  - Accepted after dev-host visual pass: search QuickPick works — query/submit/busy, type/status narrowing, open-in-reader, empty/no-results states all correct. Closing to Done.
<!-- sq:discussion:end -->
