---
id: TASK-298
sequence_id: 298
type: task
title: Disjoint block-shift offset planner (--from/--onto/--by)
status: Done
parent: FEAT-288
author: tech-lead
refs:
- TASK-297:depends-on
description: Operator integers -> validated disjoint offset -> remap + padded renames
subentities:
- local_id: ST1
  title: Offset lands the shifted block disjoint from both ranges
  status: Done
  story: US2
- local_id: ST2
  title: Rename targets minted at filename padding, content unpadded
  status: Done
  story: US4
created_at: '2026-07-06T08:47:57Z'
updated_at: '2026-07-06T09:55:27Z'
---
<!-- sq:body -->
Build the block-shift **planner** that turns operator-supplied integers into the
`{old -> new}` remap + padded renames the shared executor consumes, computing/validating
a disjoint offset so the shifted block lands strictly above both branches' ranges
(ADR-295 §2, §3). sq stays **git-agnostic**: the boundary crosses in as plain integers
only — no subprocess, no git, no merge-base, no reading `.squads.json` from another ref
anywhere in `src/`.

## Scope
- Inputs: `--from N` (required; lowest branch-local sequence number, inclusive — items with
  `sequence_id >= N` are the block to shift), and exactly one of `--onto M` or `--by n`
  (mutually exclusive).
- Let `C` = this branch's own counter (max local `sequence_id`, read from the index).
- **`--onto M`:** `delta = max(M, C) + 1 - N`. The block lands at `max(M, C) + 1`, strictly
  above both the other branch's counter and this branch's own max. Always computable,
  always safe.
- **`--by n`:** validate `N + n > C`. If it fails, **refuse** with `SquadsError` (exit 1,
  **no files touched**) and report the minimum safe offset. Additionally warn that without
  `--onto`, sq cannot certify the block clears the *other* branch's counter — that guarantee
  is the operator's on this path. Never silently auto-correct a too-small `--by`.
- Emit the remap for every local item (`seq >= N`) as `seq -> seq + delta`, preserving
  relative order and gaps. Remap targets are unpadded (`DISPLAY_ID_PADDING`); **rename
  targets are minted at filename padding** via `format_item_id(prefix, seq, db.padding)`
  (US4 — on-disk lexical sort survives even though content is unpadded per ADR-282).
- Because the new range is strictly above the old local range, no new ID string equals any
  old ID string in the remap, so single-pass `rewrite_ids` is order-independent (no
  high-to-low ordering machinery needed). Document this invariant at the planner.

## Acceptance
- `--onto M` yields a block strictly above `max(M, C)`; verified for `M > C`, `M < C`,
  `M == C`.
- `--by n` with `N + n <= C` refuses (exit 1, no filesystem mutation) and prints the min
  safe offset; a safe `--by` produces the correct remap and warns about the missing
  `--onto` certification.
- Remap preserves gaps/order; rename stems are padded to `db.padding`; content targets are
  unpadded.
- No `subprocess` / `import git` / `os.system` introduced in `src/` (grep gate stays clean).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 298 add-subtask "<title>"`; track with `sq task 298 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Offset lands the shifted block disjoint from both ranges | US2 |
| ST2 | Done |  | Rename targets minted at filename padding, content unpadded | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Offset lands the shifted block disjoint from both ranges

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — Shifted block is disjoint from the other branch's range
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Done when the offset planner lands the shifted block strictly above BOTH the other branch's counter (via --onto: delta = max(M,C)+1-N) AND this branch's own max C, and a --by n offset that fails N+n>C is refused with SquadsError / exit 1 / no files touched, reporting the minimum safe offset (ADR-295 §3). sq stays git-agnostic: --from/--onto/--by cross in as plain integers only — no subprocess/git/merge-base added to src/ (grep gate clean).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Rename targets minted at filename padding, content unpadded

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US4 — Filenames keep their padded width after a shift
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Done when the padded-disk / unpadded-content seam holds across the shift: rename targets are minted at filename padding via format_item_id(prefix, seq, db.padding) so on-disk lexical sort survives, while the remap fed to rewrite_ids uses the unpadded DISPLAY_ID_PADDING form (ADR-282). A test asserts renamed files keep the squad's filename width and that frontmatter/refs/prose read unpadded.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-06T09:55:27Z] Elias Python:
  - REV-302 F1 addressed (same scrub as TASK-297/299) and F2 addressed: strengthened the padded-filename assertion to check the digit-run width equals db.padding (was just .isdigit()), and added test_renumber_rewrites_an_unshifted_items_ref_to_a_shifted_item covering the reverse referential-intent direction.
<!-- sq:discussion:end -->
