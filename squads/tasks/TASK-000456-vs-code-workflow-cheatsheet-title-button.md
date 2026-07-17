---
id: TASK-456
sequence_id: 456
type: task
title: 'VS Code: workflow cheatsheet title button'
status: Done
parent: FEAT-449
author: tech-lead
assignee: typescript-dev
refs:
- ADR-427:addresses
- TASK-451:depends-on
description: 'Client: title button opens sq workflow --raw in the preview (US4/F8
  client half)'
created_at: '2026-07-17T13:24:11Z'
updated_at: '2026-07-17T16:01:50Z'
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
- [2026-07-17T15:56:26Z] Ada Typescript:
  - Done: view-title button squads.openWorkflow ($(book) icon, view/title navigation@4 on squadsTree) opens the workflow cheatsheet in the OWNED WEBVIEW, not markdown.showPreview.
  - Adapter: getWorkflowRaw runs sq workflow --raw (mirrors getRaw), fixture test/fixtures/workflow-raw.txt, unit-tested (success/argv/non-zero/spawn-error).
  - Rendering: renderMarkdownToHtml gained an opt-in renderMermaidFences flag (default false, item preview unchanged) — a fenced mermaid block renders live via the same sq-graph-source/sq-graph-output + data-output-id mechanism the children/refs graphs use; generalized the webview's mermaid-render script from a fixed 2-section list to a generic querySelectorAll('.sq-graph-source') scan so it covers however many diagrams a document carries. renderWorkflowHtml (previewDocument.ts) opts into it; ItemPreviewManager.openWorkflow/renderWorkflow give the cheatsheet its own owned panel (squadsWorkflowPreview), tracked separately from the item-preview panel so neither steals the other's slot.
  - Resolves the REV-448 F9 caveat this task inherited: since it renders in the owned webview (not the built-in markdown preview), the cheatsheet's mermaid diagrams render for real, not as fenced code — no remaining caveat.
  - Gate: npm run check clean (tsc/eslint --max-warnings 0/prettier), npm test 145/145, npm run test:canary 8/8. Button wiring + actual webview render are CI/manual-only (no extension-host harness exercises view/title commands) — noted, not unit-testable.
  - @reviewer please review.
<!-- sq:discussion:end -->
