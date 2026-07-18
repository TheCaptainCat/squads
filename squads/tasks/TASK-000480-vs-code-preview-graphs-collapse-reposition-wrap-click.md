---
id: TASK-480
sequence_id: 480
type: task
title: 'VS Code preview graphs: collapse, reposition, wrap, click'
status: Done
parent: FEAT-471
author: tech-lead
assignee: typescript-dev
priority: medium
description: 'Client: graph presentation F23+F24+F25 (US6 client)'
created_at: '2026-07-18T20:10:46Z'
updated_at: '2026-07-18T20:36:48Z'
---
<!-- sq:body -->
Story: US6 (REV-448 F23 + F24 + F25, Medium). **Discipline: CLIENT / TypeScript** (`clients/vscode/`). No new core surface.

## Scope

Presentation + interaction fixes to the preview's two mermaid graphs (children/subtree, ref graph).

- **F23 — collapse + reposition**: `buildGraphSection` emits `<details class="sq-graph" open>` — drop `open` so both fold by default. Move the graphs from the bottom (`<article>${bodyHtml}</article> ${graphsHtml} ${discussionHtml}`) to directly under the item's frontmatter/metadata header, above the prose body, so they're visible without scrolling. This needs the metadata header separated from the rendered body prose (two fragments with graphs injected between), or a simpler first cut placing graphs just below `<article>`'s top — exact seam is an implementation decision.
- **F24 — no clipped labels**: mermaid inits `securityLevel: 'strict'` (disables htmlLabels → non-wrapping SVG text → cropped labels). Ensure no label text is clipped — via flowchart `htmlLabels`/`wrappingWidth` config within the strict CSP if feasible, or shorter id-only labels with the title in a tooltip, or nodes sized to their text.
- **F25 — clickable nodes**: clicking a node navigates to that item, reusing the same `OPEN_ITEM_COMMAND` channel and click/auxclick split already used for `a.sq-item-link` (F10/F11). Strict mode disables click directives, so wire click handlers post-`mermaid.render` using the stable node ids `graph_to_mermaid` already emits.

## Acceptance

- Both graphs render collapsed by default and are positioned under the metadata header, above the body prose.
- No graph node label text is clipped.
- Clicking a node opens that item in the same panel; middle-click opens it in a new panel.
- Client-only: no new core/machine surface.
- TS gate parity: tsc strict + eslint zero-warnings + prettier; skew canary green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 480 add-subtask "<title>"`; track with `sq task 480 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-18T20:36:45Z] Ada Typescript:
  - F23 (collapse+reposition): buildGraphSection drops 'open'; renderOutcomeHtml now splits the --raw dossier into headerHtml/bodyHtml (splitDossierMarkdown: title+metadata-bullet block vs. prose body, falling back to empty header when it can't detect that shape e.g. a failure message); buildPreviewHtml assembles header -> graphsHtml -> body inside <article>, so both graphs sit collapsed directly under the metadata header, above the prose.
  - F24 (no clipped labels): graphDiagrams.ts's mermaidNodeLabel now emits Mermaid's markdown-string label syntax ("`text`") instead of a plain quoted string, paired with flowchart.wrappingWidth:200 in mermaid.initialize -- mermaid's documented mechanism for auto-wrapping long labels from real text-metric measurement even under securityLevel:'strict'. Markdown metachars (backtick/asterisk/underscore) are backslash-escaped so a title never turns into emphasis/code; escapeHtml still covers </>/"/&. truncate(120) is a defensive hard cap on top of the wrap.
  - F25 (clickable nodes): mermaidRenderScript stamps each rendered node with data-item-id, recovered from mermaid's own '<diagramId>-flowchart-<nodeId>-<n>' group id (nodeId is exactly mermaidNodeId's hyphen-to-underscore fold, losslessly reversible since an item id has exactly one non-word char). clientScript's shared click/auxclick delegation now matches 'a.sq-item-link, g.node[data-item-id]', reusing the same OPEN_ITEM_COMMAND channel and same-panel/new-panel split.
  - Verified the node-id regex against realistic mermaid-generated ids via a throwaway jsdom probe (not committed) before wiring it into the client script.
  - Gates: tsc --noEmit clean, eslint --max-warnings 0 clean, prettier --check clean, npm test 196/196 green, npm run test:canary 10/10 green.
<!-- sq:discussion:end -->
