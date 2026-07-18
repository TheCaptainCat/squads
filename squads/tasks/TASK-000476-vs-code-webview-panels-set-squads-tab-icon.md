---
id: TASK-476
sequence_id: 476
type: task
title: 'VS Code webview panels: set squads tab icon'
status: Done
parent: FEAT-471
author: tech-lead
assignee: typescript-dev
priority: low
description: 'Client: webview panel iconPath (US2/F16 client)'
created_at: '2026-07-18T20:10:33Z'
updated_at: '2026-07-18T20:39:44Z'
---
<!-- sq:body -->
Story: US2 (REV-448 F16, Low). **Discipline: CLIENT / TypeScript** (`clients/vscode/`). No core change.

## Scope

The webview panels (item preview + workflow cheatsheet) are created via `createWebviewPanel` with no `iconPath`, so their editor tabs show VS Code's generic default icon.

- Set `panel.iconPath` on both `createWebviewPanel` sites to the squads icon at `resources/squads-icon-vscode.svg` (already the activity-bar icon) — a single Uri, or `{light, dark}` if the single SVG doesn't read well in both themes.

## Acceptance

- Both webview panels' editor tabs show the squads icon.
- Client-only: no new core/machine surface.
- TS gate parity: tsc strict + eslint zero-warnings + prettier; `vsce ls` clean (asset ships).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 476 add-subtask "<title>"`; track with `sq task 476 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-18T20:39:38Z] Ada Typescript:
  - Set panel.iconPath on both webview panels (item preview: openNewPanel; workflow cheatsheet: openWorkflow), via a shared panelIconPath(extensionUri) helper.
  - Went with {light, dark} rather than reusing the single activity-bar SVG as-is: that SVG uses stroke="currentColor", which VS Code's activity-bar icon path re-tints via its own icon-masking, but a webview panel iconPath is drawn as a plain image with no such re-tinting -- currentColor would resolve to CSS's black default and disappear against a dark-theme tab bar. Added resources/squads-icon-vscode-{light,dark}.svg (explicit #424242/#C5C5C5 stroke, same geometry as the activity-bar source) instead of adding back any of the F13-deleted variants.
  - vsce ls confirms all three resources/ SVGs ship in the VSIX (no .vscodeignore change needed -- resources/ was never excluded; updated its explanatory comment).
  - Gates: tsc --noEmit clean, eslint --max-warnings 0 clean, prettier --check clean, npm test 196/196 green, npm run test:canary 10/10 green, vsce ls clean.
<!-- sq:discussion:end -->
