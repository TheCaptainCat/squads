---
id: TASK-439
sequence_id: 439
type: task
title: 'Core: additive title on tree --json + is_open on list/tree --json'
status: Done
parent: FEAT-100
author: tech-lead
assignee: python-dev
refs:
- ADR-427:addresses
- REV-438:addresses
description: 'Enrich machine surface: title on sq tree --json, is_open on list+tree
  --json (additive, spec-driven)'
created_at: '2026-07-17T07:45:06Z'
updated_at: '2026-07-17T08:02:51Z'
---
<!-- sq:body -->
## Owner

Core Python work — intended for **Elias Python** (python-dev). Authored here for
scope/traceability; the tech lead is not implementing it.

## Goal

Enrich the machine surface so the VS Code client can consume it directly instead
of working around gaps client-side — the same parity move already shipped for
`sq show --raw`/`--json` in TASK-434. Two additive enrichments to the frozen read
surface, resolving REV-438's two design rulings at the surface (not in the client):

- **(a) `title` on `sq tree --json`** — each tree node carries its item title, so
  a consumer renders labels from the tree alone (today the client must issue a
  second `sq list --json` and join by id to recover titles).
- **(b) `is_open` on both `sq list --json` and `sq tree --json`** — a boolean per
  item, `true` for an open status and `false` for a terminal one, so a consumer
  classifies open/closed from one payload (today the client diffs two `sq list`
  calls — default vs `--all` — to infer it).

## Additive-only (hard invariant)

This is an **additive superset**: new keys only. Nothing is renamed, removed, or
retyped. The frozen 1.0 read surface (FEAT-15) and its golden tests stay valid —
existing consumers see the exact same keys plus the new ones. Same discipline as
TASK-434's additive `--json` body/discussion keys.

## `is_open` derivation (stays spec-driven)

Derive `is_open` CLI-side from the workflow spec's terminal-status set — the
`TERMINAL`/`is_open` machinery in `_workflow.py` — **not** a hardcoded status
table in the tree/list command. `is_open = not TERMINAL(status)` for the item's
type, so a spec that renames/adds statuses stays correct with no edit here. This
mirrors how the client's own open/closed logic must remain spec-agnostic.

## Scope

- `sq tree --json`: add `title` and `is_open` to every node (root + all children,
  recursively).
- `sq list --json`: add `is_open` to every listed item. (`title` already present
  on list — confirm and leave as-is; do not duplicate/rename.)
- Both keys emitted **unconditionally** for every item, at every depth.

## Required in this task

- **Update the affected golden fixtures**: the Python goldens for these surfaces —
  `tests/goldens/tree.json`, `tests/goldens/tree_feat.json`,
  `tests/goldens/list.json`, `tests/goldens/list_feature.json`,
  `tests/goldens/override_list.json`, and any other `sq tree`/`sq list --json`
  golden — regenerated to include the new keys. Assert the byte shapes.
- **CHANGELOG note** under the 0.10 section: additive `title` (tree) + `is_open`
  (list + tree) keys on the JSON read surface.
- **Reviewer gate on the additive-only invariant**: the change must be reviewed
  specifically for "new keys only, nothing renamed/removed/retyped" — same gate
  discipline TASK-434 carried for its additive keys. Flag it for review on that
  axis explicitly.

## Acceptance criteria

- `sq tree <root> --json` nodes carry `title` and `is_open` at every depth.
- `sq list --json` items carry `is_open`.
- `is_open` is derived from the workflow spec's terminal set (no hardcoded status
  list in the command layer); a status rename in the spec needs no change here.
- No existing key renamed/removed/retyped; all prior goldens still pass after the
  additive regeneration.
- CHANGELOG updated; full Python gate green (pyright/ruff/pytest/sq check).

## Resolves

REV-438 rulings (a) [tree titles] and (b) [open/closed classification] at the
machine surface, so the client (TASK follow-up) can drop its workarounds.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 439 add-subtask "<title>"`; track with `sq task 439 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T07:51:41Z] Elias Python:
  - Done: title on every sq tree --json node; is_open (spec-derived via WorkflowSpec.is_open, no hardcoded status list) on both sq list --json and sq tree --json. Additive only — verified via byte-diff of regenerated goldens (tree.json, tree_feat.json, list.json, list_feature.json); override_list.json untouched (unrelated command).
  - Gates: scoped pytest (tree/list/json/golden/workflow) green, tests/meta green, pyright + ruff check/format clean on _main.py, sq check clean.
  - @reviewer please review for the additive-only invariant (REV-438 rulings a/b) — new keys only, nothing renamed/removed/retyped.
<!-- sq:discussion:end -->
