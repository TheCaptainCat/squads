---
id: TASK-299
sequence_id: 299
type: task
title: Add sq renumber CLI verb wiring planner to executor
status: Done
parent: FEAT-288
author: tech-lead
refs:
- TASK-297:depends-on
- TASK-298:depends-on
description: New top-level 1.0 verb; intent-preserving pre-merge shift; counter bump
subentities:
- local_id: ST1
  title: Pre-merge shift preserves referential intent
  status: Done
  story: US1
created_at: '2026-07-06T08:47:57Z'
updated_at: '2026-07-06T09:55:28Z'
---
<!-- sq:body -->
Add the new top-level `sq renumber` CLI verb, wiring the offset planner to the shared
executor so a pre-merge block-shift preserves referential intent (it runs while every
reference on the yielding branch is still unambiguous, unlike the post-merge fallback).
This is a **new public 1.0-grammar verb** (ADR-295 §1) — get the surface exactly right.

## Scope
- `sq renumber --from <N> --onto <M>` (recommended, auto minimal safe offset) and
  `sq renumber --from <N> --by <n>` (escape hatch, validated). `--onto`/`--by` are mutually
  exclusive; `--from` required. It is **NOT** a mode of `sq repair` — distinct verb, distinct
  argument shape and blast radius.
- Flow: planner (offset task) -> `{old->new}` remap + padded renames -> shared executor
  (extraction task): `rewrite_ids` over all files -> rename -> `sequence_id` resync.
- After the apply-path, **bump the counter to the new max** (renumber-specific, ADR-295 §5).
- Validate before mutating: an unsafe `--by` refuses before any file is touched. The commit
  itself mirrors `sq repair`'s own pattern — unlocked file-level rewrite/rename, then a
  single locked `IndexStore.overwrite` to land the rebuilt index — rather than wrapping the
  whole flow in `IndexStore.transaction()`. That keeps `renumber` and `repair` sharing one
  crash-recovery story (`sq repair` always reconciles the tree either way) instead of
  inventing a second commit shape for one verb.
- Errors are `SquadsError` -> clean message + exit 1 (`@handle_errors`). Help text names the
  operator recipe for reading `--onto` outside sq:
  `git show <mainref>:squads/.squads.json | jq .counter`.
- CLI smoke test + service-level test per the testing convention.

## Out of scope
- The `renumber` reflog event (its own task).
- Coexistence docs / `repair --renumber` delineation (its own task).

## Acceptance
- `sq renumber --from N --onto M` on a fixture shifts the local block strictly above
  `max(M, C)`, rewrites frontmatter/refs/prose/inline + renames files, resyncs
  `sequence_id`, bumps the counter to the new max, and — critically — a ref that pointed at
  a shifted item still points at that same item afterward (**intent preserved**; contrast
  the post-merge `--renumber` which cannot).
- `--onto` and `--by` are mutually exclusive at the CLI (usage error if both given).
- Unsafe `--by` exits 1 with no filesystem change.
- `sq --help` lists `renumber`; `sq renumber --help` shows the `--onto` recipe.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 299 add-subtask "<title>"`; track with `sq task 299 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Pre-merge shift preserves referential intent | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Pre-merge shift preserves referential intent

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — Pre-merge shift preserves referential intent
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Done when sq renumber --from N --onto M shifts the local block (seq>=N) strictly above max(M,C), rewrites frontmatter id:/refs + body prose + inline mentions, renames files, resyncs sequence_id, and bumps the counter to the new max — validated before any file is touched (an unsafe --by refuses first), then committed via the same unlocked-rewrite-then-locked-overwrite pattern sq repair already uses (not a single IndexStore.transaction() wrapper). Critically, a ref that pointed at a shifted item still points at that same item afterward (referential intent preserved, contrast post-merge --renumber which cannot). --onto/--by are mutually exclusive at the CLI; it is a standalone verb, not a repair mode (ADR-295 §1).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-06T09:48:24Z] Elias Python:
  - F3 reconciled: body/ST1 no longer say IndexStore.transaction() — the commit mirrors sq repair's own unlocked-rewrite-then-locked-overwrite pattern (via the new shared _rebuild_index_from_disk helper) instead of a second transaction shape, since sq repair already reconciles the tree on either verb's crash.
- [2026-07-06T09:55:28Z] Elias Python:
  - REV-302 fixes landed: F1 (ID citations scrubbed from added src/ lines, proof empty), F2 (see TASK-298 comment for the two test additions), F3 (task body + ST1 reconciled to describe the actual unlocked-rewrite-then-locked-overwrite commit pattern, matching sq repair, instead of IndexStore.transaction()). Full suite: 1605 passed, 1 skipped; pyright/ruff/ruff-format all clean.
<!-- sq:discussion:end -->
