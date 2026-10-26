---
id: TASK-1148
sequence_id: 1148
type: task
title: Prove the preview graph renders and share the leaf builder
status: Done
author: tech-lead
priority: medium
refs:
- MILE-1051:targets
- REV-462:addresses
- REV-465:addresses
description: 'VS Code client: mermaid under the CSP in the e2e smoke; one item-leaf
  builder for list and roster views'
subentities:
- local_id: ST1
  title: Render a mermaid graph under the CSP in the e2e smoke
  status: Done
- local_id: ST2
  title: Share one item-leaf builder between list and roster views
  status: Done
created_at: '2026-10-25T19:56:58Z'
updated_at: '2026-10-26T09:35:00Z'
---
<!-- sq:body -->
## Goal

The VS Code client's item preview is proven to render a mermaid graph under its strict CSP, and the list and roster views build item leaves from one helper. Two pieces of client work, both typescript-dev, in `clients/vscode/`.

## Read on release/0.17 HEAD (2026-10-25)

- The preview CSP is `default-src 'none'; style-src 'nonce-<n>'; script-src 'nonce-<n>'`, with mermaid vendored under `media/` and its `<style>` elements nonce-stamped after a detached parse (`previewDocument.ts`, `itemPreviewManager`). The extension-host smoke (`test/extensionHost/suite`) opens a preview but renders no graph, so the nonce path and the fate of inline `style=""` attributes under the CSP have never been observed. REV-462 F1 (medium).
- `domain/metaView.ts` and `domain/listView.ts` each keep a private `itemToLeaf` and `sortedLeaves`, written as copies and now diverged. REV-465 F1.

## Gates

`npm run lint`, `npm run typecheck`, `npm test` and `npm run test:e2e` in `clients/vscode`; no ticket ids in `clients/vscode/src` (the hygiene test enforces it).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1148 add-subtask "<title>"`; track with `sq task 1148 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Render a mermaid graph under the CSP in the e2e smoke

<!-- sq:subtask:ST1:body -->
Owner: typescript-dev. Carries REV-462 F1.

Extend the extension-host smoke so a preview of an item whose body holds a mermaid block renders an SVG: assert the rendered graph element exists, that no CSP violation was reported, and that the injected `<style>` elements carry the page nonce. Record whether inline `style=""` attributes on the SVG are dropped and whether that is visible. If the graph does not render, the fallback REV-462 F1 describes (drop the style nonce, never add `unsafe-inline` to `script-src`) is the option, and it goes back to the operator before landing.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-10-26T09:26:57Z] `typescript-dev` Ada Typescript:
  - Done. The preview graphs render under the strict CSP in the real extension host (VS Code 1.143.1, DISPLAY :0, run once in the foreground, exit 0). No fallback needed.
    
    What changed (clients/vscode only):
    - The webview cannot be read from the host, so the page now posts a `renderReport` message after its mermaid pass settles (it also posts when mermaid failed to load): graphs rendered/failed, `<style>` elements in the SVGs and how many carry the nonce and have a live sheet, inline `style=""` attributes and how many the CSS OM reflects, and every `securitypolicyviolation` seen. `parseRenderReportMessage` guards it; `ItemPreviewManager.onDidReportRender` relays it; `activate()` now returns `{ onDidReportPreviewRender }`.
    - e2e: `runTest.ts` writes a stub `sq` (node script, `squads.sqPath` via the workspace settings) that answers `show --raw`, `tree --json` and `graph --json` for SMOKE-2 from the committed fixtures. The suite opens SMOKE-2 and asserts 2 graphs rendered, 0 failed, every `<style>` nonced and applied, and no CSP violation other than `style-src-attr`.
    - Unit: `previewMessages.test.ts` (parseRenderReportMessage, 9 cases), `previewDocument.test.ts` (script carries the report and the violation listener).
    
    Measured (run output): {"rendered":2,"failed":0,"styleElements":2,"styleElementsNonced":2,"styleElementsApplied":2,"inlineStyleAttributes":58,"inlineStyleAttributesApplied":58,"violations":[]}.
    - Inline `style=""` attributes on the SVG are NOT dropped here: all 58 are reflected in el.style, and no style-src-attr violation fired. They reach the page through importNode of a parsed node, not an innerHTML string; that path is what was measured. Not measured: other VS Code versions, or the innerHTML patch path (same-item refresh re-runs the same render pass, untested in e2e).
    - Item previews do not render ```mermaid``` fences from the body (only the workflow panel does); the two structured graphs are the item preview's mermaid content.
    
    Gates: lint, typecheck clean; npm test 758 passed; test:e2e exit 0.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Share one item-leaf builder between list and roster views

<!-- sq:subtask:ST2:body -->
Owner: typescript-dev. Carries REV-465 F1.

Extract one leaf builder (and its sorted variant) into `domain/displayNode.ts` and have `listView.ts` and `metaView.ts` call it. First diff the two copies and decide which divergence is intended; state it in the handoff. If one view needs a different label or description, pass that in rather than keeping two builders.

Test: unit tests for the shared builder (label, description, tooltip, icon, closed flag, id order), and the existing list and roster view tests pass unchanged unless the handoff names an intended change.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-10-26T09:27:00Z] `typescript-dev` Ada Typescript:
  - Done. `itemLeaf(item, context, rendering)` and `sortedItemLeaves(items, render)` now live in domain/displayNode.ts; listView, metaView and recordsView call them. Records had a third copy of the same builder, so it moved too.
    
    Diff of the copies, all intended (they are the per-view `rendering` argument, nothing else differed):
    - description: list `status · assignee ?? unassigned`; roster pronouns badge + status; records status alone.
    - icon: list and records `iconForType(type, overrides)`; roster `iconForMetaType`.
    - roster only: memory count/age label suffix, memory tooltip line, memory-entry children (`labelSuffix`, `tooltipSuffix`, `children`).
    Shared: label `id  title`, tooltip, role-derived closed/hidden/colour, blocked/anchor false, numeric id order. No behaviour change: existing list, roster and records tests pass unchanged.
    
    Tests: displayNode.test.ts `itemLeaf / sortedItemLeaves` (4: label/description/icon/tooltip/children, suffixes, role closed/hidden/colour, numeric id order without mutating input).
    Gates: lint, typecheck clean; npm test 758 passed; test:e2e exit 0.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T09:35:00Z] `manager` Catherine Manager:
  - ST1 and ST2 delivered (c6ce2870, 16b6355d); REV-1162 Approved with F1 and F2 Verified; client lint, typecheck, 760 unit tests and the e2e smoke green. No visible behaviour change. Accepted under the operator's delegation.
<!-- sq:discussion:end -->
