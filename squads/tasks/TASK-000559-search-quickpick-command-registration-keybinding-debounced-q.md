---
id: TASK-559
sequence_id: 559
type: task
title: 'Search QuickPick command: registration, keybinding, debounced query, results
  + states'
status: Done
parent: FEAT-537
author: tech-lead
assignee: typescript-dev
created_at: '2026-07-21T23:19:30Z'
updated_at: '2026-07-21T23:56:23Z'
---
<!-- sq:body -->
The QuickPick surface itself (US1 + US4). Registers the command + keybinding, drives the submit/debounced query against the TASK-558 adapter method, renders the results list, and handles the empty / no-results / busy states.

## Scope
- Register a `squads.search` command in `clients/vscode/package.json` (`contributes.commands`, category "Squads") plus a keybinding, and add a Command-Palette entry. Wire the command in `clients/vscode/src/commands.ts` / `extension.ts` alongside the existing registrations.
- Open a `vscode.window.createQuickPick()` (not `showQuickPick`) so we control `onDidChangeValue` / `onDidAccept` and the `busy`/`placeholder` fields.
- Query posture: fire on submit (Enter / `onDidAccept`) or a short debounce — NOT per keystroke. One `sq search` process per query. Cancel/ignore a stale in-flight result if a newer query supersedes it (last-query-wins).
- Set `quickPick.busy = true` while a search is in flight; clear it when results arrive.
- Render each hit as a QuickPickItem: `label` = id + title, `description` = type/status, `detail` = the matched snippet(s) from the hit`s `hits[]`. Keep the transform pure/unit-testable (a helper mapping `SqSearchHit[]` → QuickPickItem-shaped data), separate from the vscode wiring.
- States (US4): empty query → a clean "type to search" placeholder, no process spawned; zero matches → a clean "no results" item/placeholder; in-flight → busy indicator. None render an error or traceback. Adapter failures surface as a notification via `describeFailure` (mirror existing error handling), not a crash.

## Grounding / constraints
- TypeScript. Reuse `getSearch` from TASK-558 for all data; do not add a second adapter path.
- Selecting a result and opening it is TASK-561; type/status narrowing is TASK-560. Keep this task to opening the palette, querying, listing, and the three states — leave a clear seam (an accept callback + a filter hook) for those two.
- Follow the existing command-registration and disposal pattern (push into `context.subscriptions`).

## Acceptance
- The command + keybinding open the QuickPick from anywhere; empty query shows the type-to-search state and spawns no process.
- Submitting a query runs exactly one `sq search` and lists id/type/title/snippet per hit; a superseded in-flight query does not clobber newer results.
- Busy indicator shows while searching; zero matches shows the clean no-results state; an adapter error shows a notification, not a traceback.
- vitest unit tests (vitest) cover the pure hit→QuickPickItem mapping (incl. multi-snippet and empty-hits rows) and the debounce/last-wins + empty-query-no-spawn logic with a stubbed adapter/timer. vscode host wiring is left to the extension-host smoke path, mirroring the existing split.
- No sq/ticket IDs in source or test names.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 559 add-subtask "<title>"`; track with `sq task 559 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T23:33:03Z] Ada Typescript:
  - QuickPick command wired (package.json + searchQuickPick.ts), domain/searchRunner.ts (debounce+last-wins) and domain/searchResults.ts (hit mapping) pure/unit-tested; accept + filter-args left as explicit seams for TASK-560/561. Gates green.
<!-- sq:discussion:end -->
