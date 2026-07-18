---
id: TASK-482
sequence_id: 482
type: task
title: 'VS Code hover: render priority/severity collection badges'
status: Done
parent: FEAT-471
author: tech-lead
assignee: typescript-dev
priority: medium
refs:
- TASK-481:depends-on
description: 'Client: badge hover, consumes US7 surface (US8/F19)'
created_at: '2026-07-18T20:10:48Z'
updated_at: '2026-07-18T21:10:32Z'
---
<!-- sq:body -->
Story: US8 (REV-448 F19, Medium). **Discipline: CLIENT / TypeScript** (`clients/vscode/`, `domain/displayNode.ts::buildTooltip`). Depends on US7's core collections surface.

## Scope

Surface priority/severity collection badges in the tree-item hover tooltip. Today `buildTooltip` shows id/type/Status/Assignee/Priority (raw code)/Blocked — severity is absent.

- Consume US7's generic per-item `badges` map (from the item `--json` surface) plus the `sq workflow collections --json` catalog to resolve each field code → glyph + label, without hardcoding emoji or field names.
- Render the badges via a `MarkdownString` tooltip so the real glyphs display.
- Spec-driven: render whatever collections the spec declares (priority, severity, and any custom axis) — do not hand-add a severity field or hardcode a badge-glyph vocabulary.

## Acceptance

- The hover tooltip shows priority AND severity (and any spec-declared collection) as rendered badges resolved from the surface + catalog.
- Zero hardcoded collection names or emoji in the client.
- Depends on US7 (F20) landing first; consume the shipped surface, recapture the client fixture from live output.
- TS gate parity: tsc strict + eslint zero-warnings + prettier; skew canary green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 482 add-subtask "<title>"`; track with `sq task 482 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-18T21:10:27Z] Ada Typescript:
  - Implemented: tree-item hover now renders spec-driven collection badges (priority, severity, any custom axis), joined through sq workflow types --json's per-type fields[] (field->collection) and sq workflow collections --json (collection->{code,label,emoji}) — new domain/badgeCatalog.ts, zero hardcoded collection/emoji names.
  - buildTooltip (displayNode.ts) now takes resolved badges instead of a hardcoded priority field; rendered as a vscode.MarkdownString (treeItemRendering.ts) with markdown hard-breaks so glyphs show on their own line. Both catalogs fetched once per refresh alongside the existing type catalog (treeDataProvider.ts + metaTreeDataProvider.ts), degrading gracefully to raw codes on fetch failure.
  - Recaptured type-catalog.json fixture (now carries fields[]); added collections-catalog.json + statuses-catalog.json fixtures from live sq output. Skew canary extended (10->14 tests) to assert the new shapes. Gates: tsc/eslint/prettier clean, npm test 231/231, canary 14/14.
<!-- sq:discussion:end -->
