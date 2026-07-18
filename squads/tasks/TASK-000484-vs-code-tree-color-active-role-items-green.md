---
id: TASK-484
sequence_id: 484
type: task
title: 'VS Code tree: color active-role items green'
status: Done
parent: FEAT-471
author: tech-lead
assignee: typescript-dev
priority: medium
refs:
- TASK-483:depends-on
description: 'Client: green active items, consumes US9 surface (US10/F26 client)'
created_at: '2026-07-18T20:10:49Z'
updated_at: '2026-07-18T21:19:50Z'
---
<!-- sq:body -->
Story: US10 (REV-448 F26 client half, Medium). **Discipline: CLIENT / TypeScript** (`clients/vscode/`). Depends on US9's core status-role surface.

## Scope

Color 'work in flight' items green in the tree, keyed generically on a spec-declared semantic role — never on the literal status string.

- Read `status_role` generically off US9's `sq workflow statuses --json` catalog: join an item's `status` string to the catalog to read its `role`, then map `role == "active"` → green in the VS Code tree (work tree + roster).
- Never hardcode which status name means 'active'.
- Composes cleanly with F7's closed-item dimming (disjoint sets — a terminal status is never `role == "active"`).

## Acceptance

- Items whose status carries `role == "active"` (bundled: InProgress, Active) render green; other items unchanged; closed-item dimming unaffected.
- Zero hardcoded status names in the client; role read via the catalog join.
- Depends on US9 (F26 machine-surface half) landing first; consume the shipped surface, recapture the client fixture from live output.
- TS gate parity: tsc strict + eslint zero-warnings + prettier; skew canary green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 484 add-subtask "<title>"`; track with `sq task 484 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-18T21:19:45Z] Ada Typescript:
  - Implemented: tree/roster items whose status carries the spec-declared 'active' role now render green, joined through sq workflow statuses --json (new domain/statusRole.ts: buildStatusRoleMap + isActiveRole) — zero hardcoded status names.
  - New DisplayNode.active flag threaded through treeMapping/listView/metaView (same pattern as .closed). Extracted the precedence decision (blocked > closed > active > none) into a pure, unit-tested domain/displayNode.ts::emphasisForNode so treeItemRendering.ts's vscode-facing iconForNode is just a presentation lookup (charts.green for active) — this made the disjoint-with-dimming claim directly testable without a VS Code host.
  - Statuses catalog fetched once per refresh alongside the existing type/collections catalogs (treeDataProvider.ts + metaTreeDataProvider.ts), graceful fallback to no-highlight on fetch failure. Gates: tsc/eslint/prettier clean, npm test 250/250 (16 files, +19 from this task), canary 14/14.
<!-- sq:discussion:end -->
