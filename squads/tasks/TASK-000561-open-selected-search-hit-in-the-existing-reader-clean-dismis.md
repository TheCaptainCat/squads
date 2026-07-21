---
id: TASK-561
sequence_id: 561
type: task
title: Open selected search hit in the existing reader; clean dismissal
status: Done
parent: FEAT-537
author: tech-lead
assignee: typescript-dev
created_at: '2026-07-21T23:19:31Z'
updated_at: '2026-07-21T23:56:25Z'
---
<!-- sq:body -->
Make a search hit a jumping-off point (US3): selecting a result opens that item in the extension's existing reader/preview, and dismissing the QuickPick returns cleanly to the prior editor/view state.

## Scope
- On `onDidAccept` of a result QuickPickItem, resolve the selected hit`s item id and open it through the existing `ItemPreviewManager` (`clients/vscode/src/itemPreviewManager.ts`) — the same owned preview panel the tree uses to open an item. Reuse the existing public open entry point (today `openFromTree(id)`); if a tree-neutral name is warranted, rename/alias it, but do NOT fork a second preview path.
- Hide/dispose the QuickPick on accept so focus lands on the opened preview.
- Dismissal (Escape / focus-out with no selection) disposes the QuickPick and leaves the prior editor/view state untouched — no panel opened, no navigation, no lingering QuickPick.

## Grounding / constraints
- TypeScript. Read-only: opening a hit performs no mutation (no transition/comment/assign) — it only reveals the item in the reader.
- Do not introduce a new rendering/preview surface; the reader already renders `sq show <id> --raw` + graphs + discussion. This task only routes a chosen id into it.
- Keep the id-resolution (QuickPickItem → item id) pure and unit-testable; the panel wiring itself is exercised by the extension-host smoke path, mirroring the existing preview split.

## Acceptance
- Selecting a result opens that exact item in the existing preview panel (reusing the owned panel per current behavior).
- Dismissing without selecting opens nothing and returns to the prior state cleanly.
- vitest unit tests (vitest) cover the QuickPickItem→id resolution and that accept invokes the preview open with the selected id (stubbed preview manager), and that dismissal invokes no open.
- No sq/ticket IDs in source or test names.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 561 add-subtask "<title>"`; track with `sq task 561 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T23:39:42Z] Ada Typescript:
  - Accept wired to ItemPreviewManager.openFromTree via a pure decideAccept (open vs submit) decision; dismissal only disposes (no navigation). Extension-host smoke suite gets a squads.search line. Gates green.
<!-- sq:discussion:end -->
