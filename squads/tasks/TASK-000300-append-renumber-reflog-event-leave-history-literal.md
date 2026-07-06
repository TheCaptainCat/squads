---
id: TASK-300
sequence_id: 300
type: task
title: Append renumber reflog event; leave history literal
status: Done
parent: FEAT-288
author: tech-lead
refs:
- TASK-299:depends-on
description: One summary event; no in-place rewrite; verify inline-mention rewrite
subentities:
- local_id: ST1
  title: Reflog + inline mentions rewritten; history left literal
  status: Done
  story: US3
created_at: '2026-07-06T08:47:58Z'
updated_at: '2026-07-06T10:15:41Z'
---
<!-- sq:body -->
Make the renumber transaction append **one** `renumber` reflog event summarizing the shift,
and leave all historical reflog lines literal — no in-place rewrite (ADR-295 §4, the sharp
one). Content-side inline mentions are already covered by `rewrite_ids` reuse; this task is
the reflog half of US3.

## Scope
- Add `renumber` to the closed reflog op vocabulary (`_index/_reflog.py` docstring list +
  wherever the op set is enforced/typed).
- Within the `sq renumber` transaction (ordered strictly after the index commit, per
  ADR-117), append exactly one `renumber` line whose `delta` is a compact summary:
  `{"from": N, "onto": M, "by": delta, "remap": {old: new, ...}}` (a summary, not a
  replayable diff — ADR-117 §4). `onto`/`by` reflect which form the operator used.
- **Do NOT** rewrite historical `target`/`delta` ID fields. Old lines keep their pre-shift
  formatted IDs — truthful history. The single appended event is the bridge a forensic
  reader / `sq reflog` resolver uses to map an earlier reference forward. Preserves
  append-only + not-a-source-of-truth + honesty (ADR-117), and Invariant 1 is untouched
  (the index never depends on the reflog).
- Confirm the content rewrite already reaches inline ID mentions in bodies (rewrite_ids
  whole-word behaviour) — add a fixture asserting a prose mention of a shifted ID is
  updated; this closes the US3 content half alongside the reflog half.

## Acceptance
- After `sq renumber`, exactly one new `renumber` line exists; its delta carries
  from/onto|by/remap; earlier lines are byte-unchanged (assert historical target strings are
  still the pre-shift IDs).
- A body-prose mention of a shifted ID is rewritten to the new ID; no reference is left
  dangling or stale in a source-of-truth surface.
- The reflog file is still one `O_APPEND` line per op (no whole-file rewrite).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 300 add-subtask "<title>"`; track with `sq task 300 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Reflog + inline mentions rewritten; history left literal | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Reflog + inline mentions rewritten; history left literal

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US3 — Reflog and inline ID mentions are rewritten, not just frontmatter
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Done when the renumber transaction appends exactly ONE append-only 'renumber' reflog event whose delta summarizes the shift ({from, onto|by, remap}), and every historical reflog line is left byte-for-byte literal — no in-place rewrite of target/delta (ADR-295 §4; append-only + not-a-source-of-truth per ADR-117 preserved). The content-side rewrite already reaches inline ID mentions via rewrite_ids; a fixture asserts a prose mention of a shifted ID is updated and that old reflog lines still carry their pre-shift IDs.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-06T10:15:41Z] Elias Python:
  - Landed: added 'renumber' to the reflog's closed op vocabulary (_index/_reflog.py docstring only — CLI --op help text left untouched, out of scope this round).
  - Service.renumber() now appends exactly one 'renumber' reflog line after the index commit (via _rebuild_index_from_disk), delta={from, onto, by, remap} with onto/by reflecting which form the operator used (the other null) — no in-place rewrite of any historical line.
  - Content-side prose-mention rewrite confirmed working via rewrite_ids reuse (already the case; added a fixture asserting it).
  - New tests (test_service.py): test_renumber_appends_a_single_event_summarizing_the_shift, test_renumber_by_form_records_by_and_leaves_onto_null, test_renumber_leaves_prior_reflog_lines_byte_for_byte_unchanged, test_renumber_rewrites_a_prose_mention_of_a_shifted_id_in_a_body.
  - Gates: pyright 0 errors, ruff check clean, ruff format clean. Full suite once: 1610 passed, 1 skipped, 0 failures. ID-citation grep over src/+tests/ added lines: only allowed '# FEAT-2'-style fixture labels, zero docstring/prose hits.
<!-- sq:discussion:end -->
