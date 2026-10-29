---
id: TASK-1257
sequence_id: 1257
type: task
title: VS Code client reads badges, display and maps_to
status: InReview
parent: FEAT-1249
author: tech-lead
assignee: typescript-dev
priority: high
refs:
- ADR-1250:implements
- MILE-1241:targets
- TASK-1254:depends-on
description: Extension types, previews and graph labels on the new shapes
subentities:
- local_id: ST1
  title: Client types on the new shapes
  status: Done
  story: US7
- local_id: ST2
  title: Mapping label from the target kind
  status: Done
  story: US4
- local_id: ST3
  title: Graph label from badges and display
  status: Done
  story: US1
created_at: '2026-10-29T19:55:12Z'
updated_at: '2026-10-29T22:33:58Z'
---
<!-- sq:body -->
## Goal

The VS Code extension reads badge values from `badges`, labels from `display` and the catalogs, and the mapping from `maps_to`, never from a field-named key (ADR-1250 sections 3 and 7; FEAT-1249 US1, US4, US7 for the client).

## Scope

- Types and adapters for the new shapes: item rows, tree and graph nodes without `priority`, sub-entity objects with `maps_to` and flat attributes and without `severity`, `story` and `extra`, `display.maps_to`.
- Graph node label from `badges` and `display`.
- Sub-entity mapping label from the target kind (the catalog's `maps_to_parent` and the parent's hosted kind), not the word "story".

## Expected files

- `clients/vscode/src/types.ts`, `src/sqAdapter.ts`, `src/itemPreviewManager.ts`, `src/domain/previewDocument.ts`, `src/domain/previewMessages.ts`, `src/domain/previewHistory.ts`, and the graph view module
- `clients/vscode/test/` (unit tests and the skew canary)

## Runs beside

Any Python task of the last pair; no shared files. It needs the wire-shape task merged.

## Working rules

- Work in your own git worktree off `origin/release/0.19`, after the wire-shape task merges.
- Gates: the extension's lint, type check and test scripts, and the `vscode-client.yml` workflow steps run locally. `sq check` clean for the items you touched.
- Comments short, present tense, no ticket IDs or history; no ticket IDs in test names.
- No bundled field or kind name in client code: labels come from `display` and the catalogs.
- Report every user-visible change in the handback for the writer; do not edit the extension's README, MARKETPLACE or CHANGELOG.
- The operator checks visual changes in a development host (the `launch-dev-host` skill); hand back with the item InReview for that.

## Tests

About 4: a sub-entity with `maps_to` set and null; a graph label built from `badges`; a mapping label from a non-bundled target kind; the skew canary updated to the new keys.

## Size

M.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1257 add-subtask "<title>"`; track with `sq task 1257 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Client types on the new shapes

<!-- sq:subtask:ST1:body -->
`types.ts` and the adapter take the new shapes: no `priority` on tree and graph nodes, sub-entity objects with `maps_to` (always present, `null` when unset) and flat attributes, no `severity`, `story` or `extra`, and `display.maps_to`. The skew canary pins the new keys.

Tests (2): a sub-entity with `maps_to` null and set; the canary on the new keys.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Mapping label from the target kind

<!-- sq:subtask:ST2:body -->
The sub-entity mapping label in previews comes from the target kind (the catalog's `maps_to_parent` and the parent type's hosted kind), not the word "story".

Tests (1): a preview of a sub-entity whose target kind is `outcome` labels the mapping `outcome`.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Graph label from badges and display

<!-- sq:subtask:ST3:body -->
The graph node label reads the badge from `badges` and its label from `display`, not a `priority` key.

Tests (1): a graph node whose squad declares `urgency` shows that badge.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T22:08:22Z] `typescript-dev` Ada Typescript:
  - Done on worktree-agent-a22b77e3534d6deb7, commit 4d31b82d (clients/vscode). Gates green: lint, tsc, prettier, npm test 768, test:canary 90 (live sq 0.19.0). test:e2e not run (needs a display).
  - Changes: tree/graph nodes and list rows drop priority/severity; sub-entity reads maps_to (not story); graph node label = lead entry of badges, shown by display.badges[field].badge_label else raw code; preview mapping label = target kind name, resolved from the maps_to local-id prefix through the kind catalog local_prefix (Story, Outcome, generic "Maps to" when unknown). Kind catalog key is maps_to_parent. Canary pins the new keys incl. a sub-entity key set.
  - Fixtures: bundled ones jq-trimmed to the new shapes; subentity-kinds-catalog regenerated from the dev tree; new override-* fixtures (show, graph, subentity-kinds) from the override squad. Regenerate for the amended wire (maps_to_kind as KindDisplay, badges on every sub-entity): show-json, list, subentity-kinds-catalog and override-show-json. The client reads neither maps_to_kind nor field-named keys, so no code change is expected.
  - Operator check in a dev host: graph diagram node labels now show the badge label with glyph (e.g. "feature, Low" with its emoji) instead of the raw code; the sub-entity head mapping label ("Story: US1" / "Outcome: OC1") in an item preview, ideally on an override-vocabulary squad. @manager
- [2026-10-29T22:33:58Z] `reviewer` Paul Reviewer:
  - Reviewed on REV-1259: changes requested (F24 medium, waits on an architect ruling; F25 low, regenerate fixtures after TASK-1254). @manager
<!-- sq:discussion:end -->
