---
id: TASK-297
sequence_id: 297
type: task
title: Extract shared renumber executor from _renumber apply-path
status: Done
parent: FEAT-288
author: tech-lead
description: Lift rewrite_ids->rename->resync into one executor both verbs call
subentities:
- local_id: ST1
  title: Reused apply-path executor drives repair --renumber unchanged
  status: Done
  story: US5
created_at: '2026-07-06T08:47:56Z'
updated_at: '2026-07-06T09:55:26Z'
---
<!-- sq:body -->
Extract the shared renumber apply-path out of `_services/_maintenance.py::_renumber`
(lines ~610–623) into one reusable executor, so both `sq repair --renumber` (post-merge
collision fixer) and the new `sq renumber` (pre-merge block-shift) drive the identical
apply-path and the machinery does not fork (ADR-295 §5).

## Scope
- Introduce a single executor that takes a `{old_id -> new_display_id}` remap plus the
  renames list (`(path, item_type, slug, new_padded_stem)`) and performs, in order:
  `rewrite_ids` over all files (frontmatter `id:`/refs + body prose + inline mentions) ->
  file rename at **filename padding** -> `sequence_id` resync. This is exactly the current
  `_renumber` tail (lines 606–623); lift it verbatim, do not change behaviour.
- Keep the **padded-disk / unpadded-content split** intact: rename targets stay at
  `format_item_id(prefix, seq, db.padding)`; remap targets stay unpadded
  (`DISPLAY_ID_PADDING`, ADR-282). The executor must not collapse these.
- Re-wire `_renumber` so its collision **planner** (`_renumber_plan`) still produces the
  remap/renames and then calls the extracted executor. `repair --renumber` behaviour is
  unchanged.
- Counter handling stays with each caller for now: `repair` reconstructs the counter via
  its index rebuild; `sq renumber` will bump to the new max (its own task). The executor
  itself does not touch the counter. (Note: ADR-295 §5 lists "counter bump" in the shared
  apply-path prose but then assigns the bump to `sq renumber` specifically — keep the
  executor counter-neutral and let each caller reconcile.)

## Reuse / pointers
- `_itemfile.py::rewrite_ids` — whole-word `\bOLD\b -> NEW` over frontmatter + prose + inline.
- `_services/_maintenance.py::_renumber` / `_renumber_plan` — the source of the extraction.
- `format_item_id(prefix, seq, db.padding)` — the filename-rename seam.

## Acceptance
- One executor entry point exists; `_renumber` calls it; no duplicated rename/resync loop.
- `sq repair --renumber` produces byte-identical output on collision fixtures (uniqueness +
  no dangling refs preserved); full suite stays green — this is a pure refactor, no
  behaviour change and no new public surface.
- The padded-filename / unpadded-content divergence is asserted by an existing or added test.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 297 add-subtask "<title>"`; track with `sq task 297 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Reused apply-path executor drives repair --renumber unchanged | US5 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Reused apply-path executor drives repair --renumber unchanged

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US5 — Pre-merge shift and post-merge --renumber coexist
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Done when the rewrite_ids -> file-rename -> sequence_id-resync apply-path lives in one reusable executor that both sq renumber and repair --renumber call (ADR-295 §5), and repair --renumber produces byte-identical results on collision fixtures with the full suite green — a pure refactor, no behaviour change, no forked machinery. The executor stays counter-neutral (each caller reconciles the counter).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-06T09:55:26Z] Elias Python:
  - REV-302 F1 addressed: dropped the ADR-000295/ADR-000282 citations from the new src/ docstrings/comments (kept in squads/** item bodies where they belong per the repo-wide-sweep convention). Proof: git diff HEAD -- src/ | grep -nE '^+' | grep -E '(ADR|FEAT|TASK|REV|BUG|EPIC)-?0*[0-9]+' is empty.
<!-- sq:discussion:end -->
