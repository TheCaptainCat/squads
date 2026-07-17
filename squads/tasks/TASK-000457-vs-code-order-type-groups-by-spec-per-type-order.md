---
id: TASK-457
sequence_id: 457
type: task
title: 'VS Code: order type groups by spec per-type order'
status: Ready
parent: FEAT-449
author: tech-lead
assignee: typescript-dev
refs:
- ADR-427:addresses
- TASK-450:depends-on
description: 'Client: sort type groups by the exposed per-type order (US5/F1 client
  half)'
created_at: '2026-07-17T13:24:11Z'
updated_at: '2026-07-17T13:59:49Z'
---
<!-- sq:body -->
Story: US5 (type-group ordering). Covers REV-448 finding F1 — the **client half**. **Depends on** the core order-surface task (per-type `order` on a `--json` machine surface).

## Scope

When grouping by type, order the type *groups* by the workflow spec's per-type `order` consumed from the new core machine surface — un-ordered types last, type-name breaks ties — instead of discovery/alphabetical order. Default result reads epic → feature → task → bug → decision → review → guide.

Must stay spec-driven: no hardcoded type list in the client; fetch the order map from `sq`.

## Requirements

- Consume the additive core surface; recapture the client fixture from live output once the core task lands.
- Strict TS gate parity (tsc strict + eslint zero-warnings + prettier).
- Unit-test the group ordering against the fixture, including an un-ordered type sorting last and a type-name tiebreak.

## Acceptance

- Type groups render in spec order (default epic→feature→task→bug→decision→review→guide).
- Un-ordered types sort last; ties break by type name.
- `npm run check` + unit tests green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 457 add-subtask "<title>"`; track with `sq task 457 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
