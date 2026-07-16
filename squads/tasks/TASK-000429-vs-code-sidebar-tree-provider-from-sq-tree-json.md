---
id: TASK-429
sequence_id: 429
type: task
title: VS Code sidebar tree provider from sq tree --json
status: Draft
parent: FEAT-100
author: tech-lead
assignee: typescript-dev
refs:
- ADR-427:addresses
- TASK-428:depends-on
created_at: '2026-07-16T13:51:28Z'
updated_at: '2026-07-16T15:58:27Z'
---
<!-- sq:body -->
## Goal

Render the squad hierarchy in a VS Code activity-bar view: a `SquadsTreeDataProvider` backed by `sq tree <root> --json`, showing each node's id/type/status/assignee and a blocked-state badge at a glance, so an operator can navigate the squad without leaving the editor.

## Scope

- A `SquadsTreeDataProvider` (VS Code `TreeDataProvider`) that maps the `sq tree <root> --json` shape (id/type/status/assignee/blocked/children) to `TreeItem`s, preserving the hierarchy.
- Per-node presentation: id + title label, type/status, assignee, and a distinct blocked-state indicator (icon/description). Terminal vs open state legible at a glance.
- An activity-bar contribution (view container + view) registering the provider.
- Errors and empty/no-`sq` states render as an error node (per the adapter's notification behavior), never a partial silent tree.

## Acceptance criteria

- The activity-bar view shows the squad hierarchy sourced from `sq tree --json` via the foundation adapter — no direct index/file reads.
- Each node surfaces status, assignee, and blocked-state; blocked nodes are visually distinguishable.
- When `sq` cannot be resolved or exits non-zero, the tree shows an error node and an actionable notification fires (no crash).
- Unit tests drive JSON → `TreeItem` mapping against the committed fixtures with no live `sq`.
- Passes the strict TS gate (`npm run check`) established by the foundation task.

## ADR-427 constraints this task must honor

- #2 Consumer contract: read the tree **only** through `sq tree <root> --json` via the foundation adapter; MUST NOT read `.claude/` or parse `.squads.json`.
- #3 Testing: JSON → `TreeItem` mapping is unit-tested against committed fixtures, runnable with no `sq` binary.

## Implementer note

sq/ticket IDs must not appear in source — name files/tests by behavior (e.g. `treeDataProvider`, not the ticket). Depends on the foundation task (skeleton + discovery + `--json` adapter + fixtures).

Implements FEAT-100 story **US1** — "Squad hierarchy in VS Code sidebar with status and blocked-state". Addresses ADR-427.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 429 add-subtask "<title>"`; track with `sq task 429 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
