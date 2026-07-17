---
id: TASK-456
sequence_id: 456
type: task
title: 'VS Code: workflow cheatsheet title button'
status: InProgress
parent: FEAT-449
author: tech-lead
assignee: typescript-dev
refs:
- ADR-427:addresses
- TASK-451:depends-on
description: 'Client: title button opens sq workflow --raw in the preview (US4/F8
  client half)'
created_at: '2026-07-17T13:24:11Z'
updated_at: '2026-07-17T15:45:16Z'
---
<!-- sq:body -->
Story: US4 (workflow cheatsheet view). Covers REV-448 finding F8 — the **client half**. **Depends on** the core `sq workflow --raw` task (clean-markdown mode).

## Scope

Add a view-title button that opens the workflow cheatsheet as rendered markdown in the preview, reusing the existing `squads:` virtual-doc + markdown-preview path items already use (`showDocumentProvider`). The button runs `sq workflow --raw` and renders its output.

## Caveat (carried from REV-448)

VS Code's built-in markdown preview does not render mermaid natively, so the cheatsheet's diagrams show as fenced code blocks in this increment — acceptable. This view can later be moved onto the custom webview (US1) to render mermaid; not in scope here.

## Requirements

- Reuse the existing `squads:` virtual-doc + markdown-preview path; do not fork a new render path.
- Strict TS gate parity (tsc strict + eslint zero-warnings + prettier).
- Capture a `sq workflow --raw` fixture and unit-test the rendering path against it.

## Acceptance

- A view-title button opens the cheatsheet in a preview.
- Content is the clean markdown from the core raw mode (tables render; mermaid shows as fenced blocks).
- `npm run check` + unit tests green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 456 add-subtask "<title>"`; track with `sq task 456 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
