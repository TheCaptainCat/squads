---
id: TASK-430
sequence_id: 430
type: task
title: 'Open sq show --raw in a read-only squads: markdown preview'
status: Draft
parent: FEAT-100
author: tech-lead
assignee: typescript-dev
refs:
- ADR-427:addresses
- TASK-428:depends-on
- TASK-434:depends-on
created_at: '2026-07-16T13:51:29Z'
updated_at: '2026-07-16T16:02:40Z'
---
<!-- sq:body -->
## Goal

Clicking a tree node opens that item's `sq show <id> --raw` clean-markdown dossier in VS Code's markdown preview, through a read-only `squads:` virtual document — so an operator reads a clean item with no frontmatter or `<!-- sq:* -->` marker noise.

## Scope

- Register a `squads:` `TextDocumentContentProvider` that, given an item id, returns the clean-markdown output of `sq show <id> --raw` — the dossier that TASK-434 makes `--raw` emit (H1 title + bold-key metadata bullets + verbatim body). Deliberately **not** the default styled `sq show` (which renders Rich box chrome) and **not** `--json`.
- A command wired to tree-node selection that opens the corresponding `squads:` URI in the markdown preview.
- The virtual document is **read-only** (no write-back, no mutation) — this is the browse-only increment.
- Errors (unresolvable `sq`, non-zero exit) surface as notifications; the preview shows the surfaced message rather than crashing.

## Acceptance criteria

- Selecting a node opens its `sq show <id> --raw` output in the markdown preview via a `squads:` virtual doc.
- Content is the clean-markdown `--raw` output — clean prose, no YAML frontmatter, no `sq:` markers, no Rich box chrome.
- The document is read-only; there is no path to mutate the item from the preview in this increment.
- Failure to render surfaces an actionable notification; no crash, no stale/blank silent preview.
- Unit tests cover id → `squads:` URI and the content-provider path against committed `sq show --raw` fixtures, with no live `sq`.
- Passes the strict TS gate (`npm run check`).

## ADR-427 constraints this task must honor

- #2 Consumer contract: feed the preview from `sq show <id> --raw` (deliberately not the default styled render, not `--json`) for clean prose; still routed through the foundation adapter/discovery; MUST NOT read `.claude/` or `.squads.json`.
- Browse-only: no write verbs (mutation is a later, additive increment).

## Implementer note

sq/ticket IDs must not appear in source — name files/tests by behavior (e.g. `showDocumentProvider`, `previewCommand`). Depends on the foundation task and on the core `sq show --raw` clean-output task.

Implements FEAT-100 story **US2** — "Clicking a tree node opens sq show --raw in markdown preview". Addresses ADR-427.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 430 add-subtask "<title>"`; track with `sq task 430 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
