---
id: TASK-507
sequence_id: 507
type: task
title: Preview panel back/forward navigation history
status: Done
parent: FEAT-506
author: tech-lead
subentities:
- local_id: ST1
  title: 'History stack: back/forward + forward-stack truncation'
  status: Done
  story: US1
- local_id: ST2
  title: 'Discoverable controls: title-bar buttons, keybinding, inert at ends'
  status: Done
  story: US2
created_at: '2026-07-20T12:26:12Z'
updated_at: '2026-07-20T12:41:17Z'
---
<!-- sq:body -->
Add per-panel back/forward navigation history to the item-preview webview, mirroring browser
back/forward semantics. Complements the recently-shipped @mention linkification: users now click
around between items and need a way back.

## Where
`clients/vscode/src/itemPreviewManager.ts` owns the preview `WebviewPanel` lifecycle. Today it
tracks per-panel current item via `openPanels: Map<WebviewPanel, string>`. Navigation flows through
`render(panel, id, mode)`, where `mode` is `'reload'` (a fresh page load for every navigation — the
default) vs `'patch'` (in-place refresh for the on-disk watcher). Back/forward re-render through the
same `'reload'` path a link-click uses.

## Approach
- Maintain a per-panel navigation **history** — a list of item ids plus a current index — alongside
  the existing current-item tracking (extend `openPanels`'s value, or add a parallel per-panel
  structure keyed by the panel). Dispose cleanup (`onDidDispose`) must drop the history too.
- Navigating to a NEW item (tree selection into the reused panel, or a link/@mention click that
  routes in-place) **pushes** onto the stack at `index+1` and **truncates** any forward entries
  (standard browser-style: the old forward stack becomes unreachable). Opening a brand-new panel
  (middle-click / no active panel) seeds a fresh single-entry history.
- Back/forward move the index and re-render the item at the new index through the existing
  navigation path (`render(panel, id)` in `'reload'` mode) — do NOT push/truncate on a back/forward
  move (it's a position change within existing history, not a new navigation).
- The watcher refresh (`refreshOpenPreviews`, `'patch'` mode) must NOT touch history — it's a
  same-item refresh, not a navigation.

## Controls (US2)
- New commands `squads.previewBack` / `squads.previewForward` registered in `commands.ts`, delegating
  to new `ItemPreviewManager` methods.
- Title-bar buttons via a `contributes.menus` `editor/title/navigation` contribution in
  `package.json`, gated so they only appear on the preview panel (`when: activeWebviewPanelId ==
  squadsItemPreview` — the item-preview `VIEW_TYPE`; do NOT show them on the workflow-cheatsheet
  panel `squadsWorkflowPreview`). Give each command an `icon` (codicon `arrow-left`/`arrow-right`).
- Optionally add Alt+Left / Alt+Right keybindings via `contributes.keybindings` with a `when` clause
  scoped to the preview panel being focused.
- **Disabled/inert at the ends:** back is inert at the oldest entry, forward at the newest, and both
  are inert on a freshly-opened panel with no navigation yet. Drive this with `setContext` context
  keys (e.g. `squads.previewCanGoBack` / `squads.previewCanGoForward`) that the manager updates on
  every render/navigation and on active-panel change, and reference them in the menu `when` /
  command enablement. Because these keys are global (not per-panel), the manager must recompute them
  whenever the active preview panel changes (`onDidChangeViewState`) so they reflect the focused
  panel's history — call this out and handle it.

## Consistency
- Keep the patch-vs-reload split and the `routeForMessage` / `routeForTreeSelection` /
  `parseOpenItemMessage` message path intact — push/truncate logic hangs off the existing routing
  decisions, don't fork a parallel path.
- Prefer extracting the pure history logic (push/truncate, back, forward, can-go-back/forward) into a
  small unit-testable helper under `domain/` (mirrors how routing lives in `domain/previewMessages`),
  with the manager doing only the vscode wiring — the manager's wiring is covered by the extension-host
  smoke test, the pure logic by unit tests.

## Dev decision to record
Whether back/forward restores the prior scroll position or lands at the top of the item. Either is
acceptable — `'reload'` naturally lands at top. State the choice in a task comment (and match US1's
"returns to the previously-viewed item" — landing at top is fine).

## Acceptance
- Per-panel, independent histories; back/forward retrace and re-advance; new-navigation-while-back
  truncates the forward stack (US1).
- Discoverable title-bar controls + keybinding on the preview panel only; both inert at history ends
  and on a fresh panel (US2).
- Unit tests for the history helper (push/truncate/back/forward/bounds); extension-host smoke test
  extended for the wiring if practical.
- `npm run check` clean in `clients/vscode` (tsc + lint + format).
- No sq/task IDs in source or test file names/text.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 507 add-subtask "<title>"`; track with `sq task 507 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | History stack: back/forward + forward-stack truncation | US1 |
| ST2 | Done |  | Discoverable controls: title-bar buttons, keybinding, inert at ends | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — History stack: back/forward + forward-stack truncation

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a user browsing linked items in the preview, I want back/forward navigation so I can retrace my steps
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Per-panel navigation history in itemPreviewManager.ts (list of ids + current index), independent across open panels. New navigation (tree/link/@mention into the panel) pushes at index+1 and truncates forward entries (browser semantics); back/forward move the index and re-render the item at the new position through the existing 'reload' render path. Watcher 'patch' refresh must not mutate history. Prefer a pure, unit-testable history helper (push/truncate/back/forward/bounds) under domain/. Acceptance: independent per-panel histories; back retraces, forward re-advances; navigating while positioned back drops the old forward stack (unreachable via forward).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Discoverable controls: title-bar buttons, keybinding, inert at ends

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a user navigating the preview, I want discoverable back/forward controls
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Discoverable back/forward controls. New squads.previewBack/previewForward commands (commands.ts -> manager methods); title-bar buttons via editor/title/navigation menu gated to the item-preview panel only (when: activeWebviewPanelId == squadsItemPreview, not the workflow panel), with arrow-left/arrow-right codicons; optional Alt+Left/Right keybindings scoped to the focused preview. Inert at ends via setContext keys (squads.previewCanGoBack/canGoForward) recomputed on every navigation AND on active-panel change (onDidChangeViewState), referenced in menu when/enablement. Acceptance: controls visible + keybinding on the preview panel; back inert at oldest, forward inert at newest, both inert on a freshly opened panel.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-20T12:35:39Z] Ada Typescript:
  - Implemented per-panel back/forward history in itemPreviewManager.ts, backed by a pure domain/previewHistory.ts helper (push/truncate/back/forward/canBack/canForward), unit-tested in test/previewHistory.test.ts.
  - Real navigation (tree selection, link/@mention click) pushes+truncates via a new navigate() path; goBack/goForward only move the index and re-render through the existing 'reload' path; refreshOpenPreviews ('patch') is untouched.
  - Controls: squads.previewBack/previewForward commands (commands.ts), title-bar buttons + Alt+Left/Right keybindings gated to activeWebviewPanelId == squadsItemPreview, inert-at-ends via a package.json command 'enablement' clause on squads.previewCanGoBack/previewCanGoForward context keys.
  - Critical wiring: context keys are workspace-global but history is per-panel, so recomputeContextKeys() runs on every onDidChangeViewState (focus change) via a new focusedPanel field, not just on navigation/back/forward -- so the buttons always reflect whichever preview tab is actually focused.
  - Decision: back/forward land at the top of the item (existing 'reload' behavior) rather than restoring prior scroll position, per the task's guidance.
  - Verified: npm run check (tsc+lint+format) clean, npm test (297 tests incl. previewHistory) clean, npm run test:e2e clean (extension host smoke test extended to exercise the back/forward commands round-tripping between two ids without throwing; the previewCanGoBack/Forward context-key values themselves aren't queryable from extension test code, so that half is reason-verified from recomputeContextKeys, noted in the suite's comment).
  - @manager ready for review.
<!-- sq:discussion:end -->
