---
id: TASK-452
sequence_id: 452
type: task
title: 'VS Code: owned WebviewPanel preview with navigable links'
status: Done
parent: FEAT-449
author: tech-lead
assignee: typescript-dev
refs:
- ADR-427:addresses
description: 'Client: replace hijacked md-preview with owned WebviewPanel + item-ID
  links (US1/F9,F10)'
created_at: '2026-07-17T13:23:56Z'
updated_at: '2026-07-17T14:29:35Z'
---
<!-- sq:body -->
Story: US1 (interactive item preview). Covers REV-448 findings F9 and F10. This is the **architectural backbone** for US1 — the graphs task builds on the panel this task establishes.

## Problem

`commands.ts` opens an item via `markdown.showPreview` — VS Code's single *dynamic* preview that follows the active editor, so opening any other markdown file replaces (steals) the item preview (F9). The built-in preview also cannot do item-to-item navigation or middle-click-new-tab (F10).

## Scope

Replace the built-in markdown-preview path (the `showPreview` / `squads:` virtual-doc render for **items**) with a `WebviewPanel` the extension owns — a dedicated tab that is never hijacked by another preview.

- Render the item dossier (from `sq show <id> --raw`) as HTML in the panel. Bundle a markdown renderer as a local asset; the webview is CSP-locked (no remote content).
- Render item-ID references (parent + refs) as links the webview intercepts (webview → extension `postMessage`): click routes to open that item in the SAME panel; middle-click (or ctrl/cmd-click) opens it in a NEW webview panel.
- Keep the existing tree wiring and the open-preview command surface working.

No new core surface — parent/refs are already in `sq show --json` / `--raw`.

## Requirements

- Strict TS gate parity (tsc strict + eslint zero-warnings + prettier), matching the Python bar (ADR-427 #3).
- CSP-locked, self-contained webview (bundled assets, no CDN).
- Unit-test the id-link extraction and the message-routing/open logic against committed fixtures (no live `sq`).
- VSIX still packages (`vsce ls`); if a bundled asset is added, `.vscodeignore` ships it.

## Acceptance

- Opening an item shows it in a dedicated owned tab that survives opening other markdown files.
- Parent/ref IDs render as links; click navigates in place, middle-click opens a new tab.
- `npm run check` + unit tests green; VSIX packages.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 452 add-subtask "<title>"`; track with `sq task 452 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T14:20:35Z] Ada Typescript:
  - Replaced the squads: virtual-doc + markdown.showPreview path with an owned WebviewPanel (src/itemPreviewManager.ts), never hijacked by other markdown files.
  - Rendering: new vscode-free src/domain/markdown.ts (lightweight hand-rolled markdown->HTML — headings/lists/code fences incl. mermaid-as-plain-code/tables/blockquotes/bold/italic/inline-code/links), no new runtime dependency, no bundler needed.
  - Navigable links (F10): item-id tokens are linkified generically (regex, spec-agnostic, no hardcoded type list) via data-item-id anchors; webview script posts {command:'openItem', id, newTab} on click/middle-click/ctrl-click (src/domain/previewMessages.ts + previewDocument.ts's inline script), routed same-panel vs new-panel through routeForMessage/routeForTreeSelection.
  - CSP: strict per-render nonce on both style and script tags, default-src 'none', no unsafe-inline, no remote content — fully self-contained inline HTML (no bundled asset files, so .vscodeignore is untouched).
  - Dropped domain/showPreview.ts + showDocumentProvider.ts + the squads: scheme entirely (superseded, no other consumer) — your call per the task, went with removal for a clean tree.
  - @reviewer: npm run check + npm test green (94/94), test:canary green (6/6), vsce ls clean (no stale compiled output from the removed files). Unit tests cover markdown rendering + link extraction (test/markdown.test.ts) and message parsing/routing (test/previewMessages.test.ts, test/previewDocument.test.ts) against fixtures incl. a real captured TASK-452 sq show --raw dossier. The webview HTML host itself (actual panel rendering/click interception in a live VS Code window) is not unit-tested — same caveat class as treeDataProvider.ts, covered only by the extension-host smoke test (test/extensionHost/suite/index.ts, updated to exercise squads.openItemPreview instead of the removed squads: provider) which is CI/manual, not part of npm test.
  - Note: resources/*.svg + a new squads-icon-vscode.svg show as modified/untracked in the tree — not from this task, looks like concurrent work on the icon-swap story; left untouched.
<!-- sq:discussion:end -->
