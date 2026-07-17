---
id: TASK-453
sequence_id: 453
type: task
title: 'VS Code: unfoldable mermaid graphs in item preview'
status: Ready
parent: FEAT-449
author: tech-lead
assignee: typescript-dev
refs:
- ADR-427:addresses
- TASK-452:depends-on
description: 'Client: children + refs mermaid graphs in the webview (US1/F11)'
created_at: '2026-07-17T13:23:56Z'
updated_at: '2026-07-17T13:59:46Z'
---
<!-- sq:body -->
Story: US1 (interactive item preview). Covers REV-448 finding F11. **Depends on** the owned-WebviewPanel foundation task — it renders into that panel.

## Scope

In the owned `WebviewPanel`, render two **separate**, independently collapsible (unfoldable) mermaid diagrams:

1. The item's children/subtree — from `sq tree <id> --json` (`id/type/title/status/priority/assignee/blocked/is_open` + nested `children`).
2. The item's ref graph — from `sq graph <id> --json` (nested `id/type/status/edge_kind/direction/children`; `edge_kind` is always `depends-on`, `direction` in/out).

Bundle a mermaid renderer as a local webview asset (the built-in md preview cannot render mermaid; it must be self-contained and CSP-safe). Build each diagram's mermaid source client-side from the JSON shapes. Each graph lives in its own collapsible section, expandable/collapsible independently.

Optional (note, don't block): make graph nodes navigable by reusing the foundation task's link-routing.

## Requirements

- Mermaid bundled locally (no CDN — CSP-locked webview).
- Strict TS gate parity (tsc strict + eslint zero-warnings + prettier).
- Unit-test the JSON→mermaid builders against committed `tree`/`graph --json` fixtures (capture from live output).
- VSIX packages with the bundled renderer (`vsce ls`; `.vscodeignore` ships the asset).

## Acceptance

- The preview shows both graphs as rendered mermaid, each independently collapsible.
- Graphs reflect live children/refs for the item.
- `npm run check` + unit tests green; VSIX packages.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 453 add-subtask "<title>"`; track with `sq task 453 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
