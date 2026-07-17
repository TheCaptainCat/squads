---
id: TASK-429
sequence_id: 429
type: task
title: VS Code sidebar tree provider from sq tree --json
status: Done
parent: FEAT-100
author: tech-lead
assignee: typescript-dev
refs:
- ADR-427:addresses
- TASK-428:depends-on
created_at: '2026-07-16T13:51:28Z'
updated_at: '2026-07-17T07:41:46Z'
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
- [2026-07-16T18:50:45Z] Ada Typescript:
  - SquadsTreeDataProvider (src/treeDataProvider.ts) sources the hierarchy from sq tree --json via the adapter; pure JSON->DisplayNode mapping lives in src/domain/treeMapping.ts (vscode-free, unit-tested against the committed tree.json fixture).
  - Reserved types (role/skill/operator) filtered at every depth by exact type string (src/domain/reservedTypes.ts) -- spec-agnostic, no dependence on the 7 work-item type names.
  - Per-node: label = id (+ title when known -- see discussion), description = 'status · assignee', tooltip carries priority + blocked overflow; blocked nodes get both a themed icon color and a ' · blocked' description suffix.
  - Gap found + worked around: sq tree --json genuinely carries no title field (only id/type/status/priority/assignee/blocked/children -- confirmed against real output). Labels enrich with title via a second sq list --json fetch (already an allowed FEAT-100 surface), joined by id; degrades gracefully to id-only labels if that second fetch fails. Flagging since the acceptance text assumed title was in the tree surface.
  - Errors (no sq found / non-zero exit) render a single error DisplayNode + fire a VS Code notification, never a partial/silent tree; spawn-error also invalidates the cached sq invocation so the next refresh re-probes.
  - npm run check clean, npm test 67/67 green. Verification honesty: no live VS Code extension host available in this environment -- verified via npm run check + unit tests (domain/treeMapping.test.ts) + reading the wiring in treeDataProvider.ts/extension.ts; live extension-host smoke-testing is deferred to CI/manual.
  - @reviewer ready for review.
<!-- sq:discussion:end -->
