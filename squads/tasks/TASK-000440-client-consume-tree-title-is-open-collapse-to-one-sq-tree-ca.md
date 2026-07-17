---
id: TASK-440
sequence_id: 440
type: task
title: 'Client: consume tree title + is_open, collapse to one sq tree call'
status: Draft
parent: FEAT-100
author: tech-lead
assignee: typescript-dev
refs:
- ADR-427:addresses
- REV-438:addresses
- TASK-439:depends-on
description: Rewire extension onto enriched surface; drop title-join + list diff;
  single sq tree call; recapture fixtures
created_at: '2026-07-17T07:45:19Z'
updated_at: '2026-07-17T07:45:38Z'
---
<!-- sq:body -->
## Owner

Client TypeScript work — intended for **Ada Typescript** (typescript-dev).
Authored here for scope/traceability; the tech lead is not implementing it.

## Goal

Rewire the VS Code extension to consume the newly-enriched machine surface (the
core task's additive `title` on `sq tree --json` and `is_open` on both
`sq list --json` and `sq tree --json`), dropping the client-side workarounds that
REV-438 flagged. **Depends on the core enrichment task landing first** — the new
keys must exist before the client reads them.

## Scope

- **Tree labels from `sq tree --json` directly.** Render node titles from the
  tree payload's new `title` field. Drop the join-by-id second `sq list --json`
  fetch (`buildTitleLookup`) that today recovers labels — the tree is now
  self-sufficient for labels.
- **Open/closed from `is_open`.** Classify each item open vs terminal from the
  `is_open` boolean. Drop the double-`sq list` diff (default vs `--all`) that
  today infers state — one payload now carries it.
- **Collapse the hierarchy render to a single `sq tree --json` call.** With titles
  and `is_open` on the tree, the non-flat/hierarchy refresh path needs exactly one
  spawn (`sq tree --json`), not three (tree + list --all + list). This also
  closes REV-438 F1 (the redundant open-only `sq list` on hierarchy refresh) as a
  natural consequence — note it in the handoff.
- Keep the flat/grouped view's data source correct: it may still need
  `sq list --json` for the flat listing, but it now reads `is_open` from that same
  single payload rather than diffing two calls.

## Required in this task

- **Recapture the committed fixtures** with the new fields:
  `clients/vscode/test/fixtures/tree.json` and
  `clients/vscode/test/fixtures/list.json`, captured from real enriched
  `sq … --json` output (not hand-edited).
- **Update unit tests** for the JSON→DisplayNode mapping and the open/closed
  classification to assert against the new fields (title from tree, `is_open`
  boolean) rather than the old join/diff logic.
- **Keep the strict gate green**: `npm run check` (tsc strict + eslint
  zero-warnings + prettier) and `npm test` all pass.
- **Keep the item-ID hygiene guard green** (`test/hygiene.test.ts`) — no sq/task
  IDs leak into client source, fixtures, or README.

## Acceptance criteria

- Hierarchy refresh issues a single `sq tree --json` spawn; no second `sq list`
  for titles, no `sq list` diff for state.
- Tree labels come from the tree payload's `title`; open/closed from `is_open`.
- Fixtures recaptured from live enriched output; unit tests updated and green.
- Strict gate + hygiene guard green.

## Addresses

REV-438 rulings (a) and (b) in the client; incidentally resolves F1 (redundant
open-only list on hierarchy refresh) by collapsing to one call.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 440 add-subtask "<title>"`; track with `sq task 440 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
