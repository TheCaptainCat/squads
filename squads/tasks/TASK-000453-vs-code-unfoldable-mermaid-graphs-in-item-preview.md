---
id: TASK-453
sequence_id: 453
type: task
title: 'VS Code: unfoldable mermaid graphs in item preview'
status: Done
parent: FEAT-449
author: tech-lead
assignee: typescript-dev
refs:
- ADR-427:addresses
- TASK-452:depends-on
description: 'Client: children + refs mermaid graphs in the webview (US1/F11)'
created_at: '2026-07-17T13:23:56Z'
updated_at: '2026-07-17T15:10:04Z'
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
- [2026-07-17T14:58:36Z] Ada Typescript:
  - Implemented F11 (two collapsible mermaid graphs) + REV-461 F2 (link scheme allowlist).
  - Builders: src/domain/graphDiagrams.ts — buildSubtreeMermaid(SqTreeNode[]) from sq tree <id> --json (flowchart TD, parent-->child, no edge label); buildRefGraphMermaid(SqGraphNode) from sq graph <id> --json --all (flowchart LR, dedup by (from,to,label), 'depends on'/'required by' for depends-on else the kind verbatim, mirrors the core CLI's graph_to_mermaid convention). Both pure, unit-tested against literal cases + the new committed fixtures test/fixtures/graph.json (live sq graph FEAT-449 --all --depth 2) and the existing tree.json.
  - Adapter: sqAdapter.ts gains getGraph (+ isSqGraphNode shape guard, types.ts SqGraphNode) calling 'graph <id> --json --all'; refactored getTree/getList/getGraph/getRaw onto a shared runSqRaw+runSqJson/runSqJsonObject (no behavior change, existing tests untouched).
  - Webview: itemPreviewManager.ts fetches show --raw + tree + graph in parallel per render; each graph degrades to an inline message (not a second notification) on its own fetch failure. previewDocument.ts adds two native <details class="sq-graph" open> sections (independently foldable, no JS needed for fold/unfold) after the dossier <article>, each with a hidden <pre class="sq-graph-source"> (escaped mermaid text) + output <div>.
  - Mermaid bundling under the strict CSP (unchanged: default-src 'none'; style-src/script-src 'nonce-*', no unsafe-inline/unsafe-eval added): mermaid's dist/mermaid.min.js (the browser IIFE build with every diagram type statically included -- no dynamic import()) is vendored via npm run compile -> scripts/copy-mermaid.js -> media/mermaid.min.js (git-ignored, reproducible, like out/), loaded through a nonce'd <script src> using webview.asWebviewUri against a media/-scoped localResourceRoots. Verified by reading mermaid's source that its render() creates a real (un-nonced) <style> tag for the diagram CSS -- would be silently disabled by our CSP if inserted as-is. Fix: the client script parses the returned svg via DOMParser (detached, no CSP), stamps our render nonce onto every <style> found, THEN inserts the resulting nodes into the live DOM -- so the stylesheet already carries a matching nonce when it connects. Zero CSP relaxation. Flagging for review: this nonce-injection technique is not exercised by any automated test here (needs a real Chromium/webview host) -- if it doesn't pan out at runtime, the documented fallback (in previewDocument.ts's mermaidRenderScript comment) is a narrowly-scoped style-src 'unsafe-inline' (never script-src).
  - REV-461 F2: markdown.ts renderLink now allowlists http/https/mailto for [text](url); a url that is itself a bare item id routes through the same internal sq-item-link mechanism; anything else (javascript:/data:/vbscript:/relative/protocol-relative) is dropped to plain escaped text. Marked Fixed.
  - Gate: npm run check clean, npm test 122/122 (was 89 -- hygiene guard included), npm run test:canary 8/8 (extended from 6 -> added an sq graph --json describe block covering the new getGraph adapter surface, same live-vs-fixture pattern as tree/list). vsce ls confirmed clean (media/mermaid.min.js ships, no src/test/node_modules leak); vsce package succeeded (~996KB VSIX; vsce warns mermaid.min.js is large (3.4MB uncompressed) -- expected/inherent to bundling mermaid, flagging FYI not a defect.
  - Not run here (sandboxed, no display): the actual mermaid render in a live webview host -- structural correctness (CSP, nonce injection, DOM wiring) is verified by code inspection + unit tests, but the visual render itself needs the extension-host smoke test / manual VS Code check per the task's own note.
  - Note: clients/vscode/resources/*.svg + a new squads-icon-vscode.svg show as pre-existing uncommitted changes in the working tree (timestamps ~2h before this session) -- not touched by this task, looks like in-flight F13 work from elsewhere.
  - @reviewer ready for review.
<!-- sq:discussion:end -->
