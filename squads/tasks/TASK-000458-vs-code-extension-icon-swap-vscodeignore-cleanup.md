---
id: TASK-458
sequence_id: 458
type: task
title: 'VS Code: extension icon swap + .vscodeignore cleanup'
status: Done
parent: FEAT-449
author: tech-lead
assignee: typescript-dev
refs:
- ADR-427:addresses
description: 'Client: use squads-icon-vscode.svg, delete 6 old variants, fix .vscodeignore
  (US6/F13)'
created_at: '2026-07-17T13:24:12Z'
updated_at: '2026-07-17T16:05:36Z'
---
<!-- sq:body -->
Story: US6 (extension icon swap). Covers REV-448 finding F13.

## Scope

- Use `resources/squads-icon-vscode.svg` (viewBox 0 0 64 64, currentColor fill+stroke — activity-bar-suitable) as the activity-bar icon in `package.json`'s `viewsContainers` entry (currently `squads-icon-mono.svg`).
- Delete the other 6 svg variants: `squads-icon-mono.svg`, `squads-icon-mono-black.svg`, `squads-icon-mono-white.svg`, `squads-icon-color.svg`, `squads-icon-color-black.svg`, `squads-icon-color-white.svg`.
- Update `.vscodeignore` (its current exclusion list names the old variants) so the VSIX ships only `squads-icon-vscode.svg` from `resources/`.

## Requirements

- Verify via `vsce ls` that only `squads-icon-vscode.svg` ships from `resources/`.
- Strict TS gate parity green.

## Acceptance

- Activity bar shows the dedicated VS Code icon.
- The 6 old variants are deleted; `.vscodeignore` updated.
- `vsce ls` confirms only `squads-icon-vscode.svg` ships from `resources/`.
- `npm run check` green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 458 add-subtask "<title>"`; track with `sq task 458 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T16:04:21Z] Ada Typescript:
  - Icon swap done: package.json activity-bar icon -> resources/squads-icon-vscode.svg; deleted the 6 old variants (mono/mono-black/mono-white/color/color-black/color-white); .vscodeignore's now-stale exclusion block removed (nothing left in resources/ to exclude). npm run check + npm test (145/145) + npm run test:canary (8/8) green; sq check clean. vsce ls confirms exactly one resources/ entry: squads-icon-vscode.svg. @reviewer
<!-- sq:discussion:end -->
