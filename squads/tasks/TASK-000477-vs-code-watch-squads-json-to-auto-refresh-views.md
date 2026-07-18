---
id: TASK-477
sequence_id: 477
type: task
title: 'VS Code: watch .squads.json to auto-refresh views'
status: Done
parent: FEAT-471
author: tech-lead
assignee: typescript-dev
priority: medium
description: 'Client: fs watcher auto-refresh (US3/F17 client)'
created_at: '2026-07-18T20:10:33Z'
updated_at: '2026-07-18T20:46:57Z'
---
<!-- sq:body -->
Story: US3 (REV-448 F17, Medium). **Discipline: CLIENT / TypeScript** (`clients/vscode/`). No new core JSON surface.

## Scope

Tree views + item preview refresh only on explicit command today; on-disk changes (an agent runs `sq`, a `git pull`) leave the views stale until manual refresh.

- When the squad resolves to a local `file:` path, watch `<squad-dir>/.squads.json` via `vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(squadDirUri, '.squads.json'))`; on `onDidChange`/`onDidCreate`/`onDidDelete`, auto-refresh the activity views (`treeDataProvider`/`metaTreeDataProvider`) and any open item preview.
- Debounce/coalesce: the index is written atomically (`os.replace`), so one change lands as create+change — collapse them.
- Skip watching when the resolved squad dir isn't a local file path; dispose the watcher with the extension.

Prereq (client-side resolution detail, not a contract change): the extension must know the resolved squad-dir path, not just the `sq` binary location — mirror `sq`'s own workspace-relative walk-up resolution.

## Acceptance

- Editing/running `sq` against a local squad auto-refreshes views + open preview with no manual refresh.
- A remote/non-file squad path skips the watcher (no error).
- Watcher disposed on `deactivate`; rapid atomic writes coalesce to a single refresh.
- Client-only: no new core/machine surface.
- TS gate parity: tsc strict + eslint zero-warnings + prettier; skew canary green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 477 add-subtask "<title>"`; track with `sq task 477 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-18T20:46:54Z] Ada Typescript:
  - Implemented: domain/squadDir.ts (pure, client-side .squads.toml walk-up mirroring _paths.py::find_config/resolve — no core change needed) + createNodeSquadDirEnvironment (nodeEnvironment.ts) + squadWatcher.ts (vscode FileSystemWatcher on <squad-dir>/.squads.json, 150ms debounce coalescing create+change, no-op when workspace folder isn't file: scheme or no .squads.toml found).
  - extension.ts wires it to refresh treeDataProvider + metaTreeDataProvider + all open item-preview panels (ItemPreviewManager now tracks every open panel -> item id in openPanels, refreshOpenPreviews() re-renders all of them, not just the reused one).
  - TS gate: tsc/eslint/prettier clean, vitest 207/207 (12 new squadDir.test.ts cases), canary 10/10.
<!-- sq:discussion:end -->
