---
id: TASK-1148
sequence_id: 1148
type: task
title: Prove the preview graph renders and share the leaf builder
status: Draft
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
  status: Todo
- local_id: ST2
  title: Share one item-leaf builder between list and roster views
  status: Todo
created_at: '2026-10-25T19:56:58Z'
updated_at: '2026-10-25T19:57:19Z'
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
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
