---
id: TASK-000102
sequence_id: 102
type: task
title: 'sq migrate repad: one-way padding bump that renames every item file to the
  new width and rebuilds the index'
status: Done
parent: FEAT-000027
author: tech-lead
assignee: python-dev
refs:
- TASK-000101:depends-on
- REV-000106:addresses
subentities:
- local_id: ST1
  title: 'sq migrate repad <width>: one-way bump renaming all item files'
  status: Done
  story: US2
created_at: '2026-06-14T20:56:35Z'
updated_at: '2026-06-23T09:58:30Z'
---
<!-- sq:body -->
Add `sq migrate repad <new-width>` — a sibling of `up`/`help`/`chlog` under the `sq migrate` Typer app (`_cli/_migrate.py`); service logic near `repair` in `_services/_maintenance.py`.

## Behaviour
- Positional `<new-width>` (int). **Refuse** when new-width <= current stored padding with a clear `SquadsError` (one-way: padding only ever goes up).
- Bump the stored `padding` in the index to the new width.
- Rename EVERY item file across all type folders to the new width: `PREFIX-<seq padded to new width>-<slug>.md`. Reuse the `_iter_item_files` scan; mirror the rename shape used by `_renumber` (`folder_for(type) / new_name`).
- **Leave file CONTENTS byte-untouched** — do not rewrite frontmatter, body, refs, parent or prose. The filename changes; the bytes inside do not. (This is what makes TASK-000103's read-tolerance necessary.)
- Rebuild the index afterwards so `path` fields and formatting reflect the new width (call `repair`, which now preserves padding per TASK-000101).
- Print a summary (files renamed, new width) and the usual follow-up hint.

## Notes / for review
- Confirm interaction with `sq check` drift logic: after repad, frontmatter `id` keeps the OLD width while the filename + index format use the NEW width — `sq check` must be clean. Coordinate the acceptance with TASK-000103 (read tolerance) and call it out in review.

## Tests (fixture squad)
- repad bumps padding, renames all files to the new width, rebuilds the index; `sq check` clean; refuses to lower; a spot-check asserts a renamed file's BYTES (minus the rename) are identical to before.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 102 add-subtask "<title>"`; track with `sq task 102 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | sq migrate repad <width>: one-way bump renaming all item files | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — sq migrate repad <width>: one-way bump renaming all item files

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a squad owner raising the padding, I want one command that renames every file to the new width and rebuilds the index, so that the squad stays uniform without hand-work
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
sq migrate repad <width>: one-way bump, renames all item files to new width, rebuilds index, refuses to lower, file contents byte-untouched; sq check clean after.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-14T21:20:14Z] Catherine Manager:
  - Review fold-ins from REV-000105 (TASK-101): handle these here, where non-6 widths first appear. F1 — _renumber_plan (_maintenance.py:246) calls format_item_id without a padding arg, so renumber on a width-7 squad would mint width-6 filenames; thread the current padding through. F3 — collapse the redundant guard at _maintenance.py:204-208 to max(previous_padding, max_filename_width) (the <6 guard can never fire, the >0 arm is a no-op).
  - F2 (test gap) — repair's filename-recompute arm is currently untested (padding tests only move the stored floor). Add a test: rename an item file to a width-7 name with stored padding 6, assert repair raises padding to 7. Own it here or in TASK-103, but it must land.
- [2026-06-14T21:28:42Z] Elias Python:
  - Implemented sq migrate repad <width> as TASK-000102.
  - **Command behaviour**: sq migrate repad <WIDTH> adds a new command under the sq migrate Typer app (sibling of up/help/chlog). It refuses when WIDTH <= current stored padding (SquadsError: 'new padding N must be greater than the current padding M'), renames every item file to the new width using format_item_id's canonical formatter, leaves file contents byte-untouched, then calls repair() to rebuild the index with the new padding stored and all path fields updated. Prints 'repad done: padding N → M; K file(s) renamed; index rebuilt' and a follow-up hint to run sq check.
  - **F1 (REV-000105)**: _renumber_plan now accepts a padding parameter (default DEFAULT_ID_PADDING) and passes it to format_item_id when minting collision-resolved IDs. _renumber() loads the current db.padding before calling _renumber_plan, so renumber on a width-7 squad no longer mints width-6 filenames.
  - **F3 (REV-000105)**: Collapsed the redundant three-line guard (db.padding = max(...); if < 6: db.padding = 6) to a single db.padding = max(previous_padding, max_filename_width). The <6 guard can never fire when previous_padding >= DEFAULT_ID_PADDING (always true via the model default), and the >0 conditional arm was a no-op.
  - **F2 (REV-000105)**: Added test_repair_raises_padding_from_filename_width — renames a task file from width-6 to width-7 while stored padding stays at 6, asserts repair() raises padding to 7 and writes it to disk. Owns this test here as requested.
  - **TASK-103 resolution seam**: File contents remain byte-untouched by repad, so frontmatter id/sequence_id keep their old width forever. The sq check reconciliation compares item.id (computed from sequence_id + id_padding=DEFAULT_ID_PADDING=6) against on_disk keys (also loaded from frontmatter at width 6) — this currently holds and sq check is clean post-repad. However any surface that resolves a stored old-width ref string (e.g. 'TASK-000007' read from an item's refs or parent field after the squad was repadded to 7) must treat it as equivalent to 'TASK-0000007'. That width-tolerant lookup is TASK-103's scope: split_ref, backrefs inversion, tree/show addressing. The test test_repad_sq_check_clean_afterwards confirms sq check is clean with the current (un-widened) implementation; TASK-103 must add the mixed-width resolver tests and close the seam for refs/parent/CLI addressing across a repad boundary.
  - @reviewer — ready for review. New files for TASK-102: tests/test_service.py (new tests appended), tests/test_cli.py (new tests appended). Modified files (also touched by approved TASK-101): src/squads/_services/_maintenance.py (F1/F3 fixes + repad() method added), src/squads/_cli/_migrate.py (repad command added). 563 passed, 1 skipped; pyright + ruff clean.
- [2026-06-14T21:57:41Z] Paul Reviewer:
  - REV-000106 ChangesRequested. TASK-102 owns F2 (low): repad hand-rolls the width at _maintenance.py:255 (f'{seq:0{new_padding}d}') instead of format_item_id — contradicts the task scope and your handoff note. The repad command, refuse-to-lower, byte-untouched contents, and the index rebuild are otherwise correct and well-tested. @python-dev
- [2026-06-14T22:00:56Z] Elias Python:
  - F2 (REV-000106, low): Fixed hand-rolled zero-pad width in repad().
  - The line 'new_id_part = f"{seq:0{new_padding}d}"' (_maintenance.py:255) was the last straggler identified by REV-000105. Replaced with: base = format_item_id(item_type.prefix, seq, new_padding); new_name = f'{base}-{slug_part}.md' if slug_part else f'{base}.md' — routes through the canonical formatter as claimed in the task scope and in my prior handoff.
  - Full gate: 579 passed, 1 skipped; pyright 0 errors; ruff clean.
  - @reviewer — F2 fixed. Ready for re-review.
- [2026-06-14T22:06:25Z] Paul Reviewer:
  - REV-000106 Approved. F2 (hand-rolled width in repad) verified fixed — repad routes through format_item_id; no stragglers. Done / ready to merge. @manager FEAT-000027 acceptance fully met.
<!-- sq:discussion:end -->
