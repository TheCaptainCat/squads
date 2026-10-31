---
id: BUG-1022
sequence_id: 1022
type: bug
title: Sub-entity body write raises KeyError; check silent
status: Verified
author: qa
refs:
- REV-1020
- MILE-1051:targets
description: 'Missing subtask body/block or discussion region: raw traceback on write,
  no check finding'
created_at: '2026-10-15T20:51:12Z'
updated_at: '2026-10-25T17:52:50Z'
priority: low
---
<!-- sq:body -->
## Summary

A sub-entity body write on a task whose subtask block, or whose `sq:subtask:ST1:body` region, has been removed ends in a raw `KeyError` traceback instead of a `SquadsError`. `sq check` reports nothing for either shape, and nothing for a task whose `sq:discussion` region is removed. Found in REV-1020 finding F2; the code path is untouched by the change under review.

## Reproduction

Released `sq` 0.15.0, in a fresh scratch squad (`sq init --backend none --roles minimal --default-names`):

1. `sq create task t --author manager` (TASK-2), then `sq task 2 add-subtask st`.
2. Delete the two marker comment lines for the subtask body region (tags `sq:subtask:ST1:body` and `sq:subtask:ST1:body:end`) from the task file.
3. `sq task 2 subtask 1 body -m x` (same with `--append`).
4. Repeat from a fresh copy with the whole `sq:subtask:ST1` block removed (from the `sq:subtask:ST1` open marker through its `:end` marker).
5. Repeat with a task whose `sq:discussion` pair is removed: `sq check`, then `sq task 2 comment --as manager -m hi`.

## Expected

Steps 3 and 4: one `error:` line (exit 1, no traceback) naming the missing region and the remedy, file and index unchanged. `sq check` reports a declared sub-entity whose block or body region is missing, and a work item whose `sq:discussion` region is missing.

## Actual

- Steps 3 and 4: exit 1 with a rich traceback ending in `KeyError: "section 'subtask:ST1:body' not found"`. The file is left unchanged.
- `sq check` prints `no issues` for both shapes (only the unrelated unwritten-body warning for ST1 appears).
- Step 5: `sq check` is silent on the missing discussion region; `comment` already fails cleanly with `error: no discussion section 'discussion' in TASK-2 (was it scaffolded?)`.

## Versions

`sq` 0.15.0 (released tool) driven; dev tree at 953a07ae read only.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T17:52:17Z] `qa` Mara Tester:
  - Verified on HEAD 68e96aea under the manager ruling (write restores the region; check reports none). TASK with ST1: body pair removed, then subtask 1 body -m and --append both succeed (region re-created at the subtask body position, text stored), no traceback; whole ST1 block removed then body -m restores the block; item discussion pair removed then comment works; subtask discussion pair removed then comment works; check clean after each. Cosmetic only: removing just the item discussion markers leaves the old heading and a second "## Discussion" heading is added after the comment.
<!-- sq:discussion:end -->
