---
id: TASK-455
sequence_id: 455
type: task
title: 'VS Code: meta-items view section'
status: Ready
parent: FEAT-449
author: tech-lead
assignee: typescript-dev
refs:
- ADR-427:addresses
description: 'Client: second activity-bar view for role/skill/operator under 3 buckets
  (US3/F12)'
created_at: '2026-07-17T13:23:58Z'
updated_at: '2026-07-17T13:59:47Z'
---
<!-- sq:body -->
Story: US3 (meta-items view section). Covers REV-448 finding F12. Client-only, no new core surface.

## Scope

Add a **second view** within the Squads activity-bar container: `contributes.views.squads` gets a second entry with its own `TreeDataProvider`, alongside the existing work tree (the way Explorer stacks folder-tree + outline + timeline as separate collapsible sections).

It hosts the meta/reserved items — role, skill, operator — that the main work tree deliberately excludes, bucketed under 3 fixed subfolders: **Roles**, **Skills**, **Operators**. Not groupable/filterable like the work tree — just the 3 buckets.

Data: `sq list --json` filtered to the 3 reserved types — the complement of the work tree's existing reserved-type exclusion (`reservedTypes.ts`). Reuse that reserved-type set rather than introducing a second hardcoded list.

## Requirements

- Reuse the client's existing reserved-type definition (spec-driven complement).
- Strict TS gate parity (tsc strict + eslint zero-warnings + prettier).
- Unit-test the bucketing (role/skill/operator → the 3 folders) against a fixture.

## Acceptance

- A second collapsible section lists role/skill/operator items under the 3 fixed buckets.
- Selecting a meta item opens its preview.
- `npm run check` + unit tests green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 455 add-subtask "<title>"`; track with `sq task 455 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
