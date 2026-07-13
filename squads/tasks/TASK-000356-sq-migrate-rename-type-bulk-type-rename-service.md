---
id: TASK-356
sequence_id: 356
type: task
title: 'sq migrate rename-type: bulk type rename service'
status: Done
parent: FEAT-281
author: tech-lead
subentities:
- local_id: ST1
  title: Bulk rename-type service under rename-specific validation
  status: Todo
  story: US1
created_at: '2026-07-09T21:34:34Z'
updated_at: '2026-07-13T09:27:36Z'
---
<!-- sq:body -->
Implements US1. Add the bulk rename-type service: rename_type(old_type, new_type) that bulk-moves every item of old_type to new_type in one transaction, reusing the primitive extracted in TASK-355.

Home: new mixin RenameMixin in src/squads/_services/_rename.py, composed into the Service facade in _service.py (sibling of RetypeMixin). Keeps _retype.py focused and avoids growing that module. (Open question for the lead/reviewer: new module vs. a second method on RetypeMixin — default to new module.)

Validation, all fail-closed BEFORE any mutation (transaction rolls back, no partial rewrite): both old_type and new_type must be work types (spec.work_types()); new_type must already be declared in the active spec (bundled or .overrides/workflow.toml) — this feature does NOT declare it; old_type != new_type; reject a reserved meta-type (role/skill/operator) with a clear error; refuse if any live child of any renamed item would get an invalid parent type under new_type (reuse the spec.parent_allowed check retype does per item).

Rename semantics (differ from retype deliberately, per re-baseline #2): sub-entities carry over unchanged (NO sub-entity refusal); status carries over unconditionally (call the TASK-355 primitive with carry_status=True — never reset). A rename target is expected to declare a workflow-compatible machine.

Bulk mechanics: open ONE store.transaction(); collect every item of old_type; build the combined {old_id:new_id} remap for all of them; apply per-item self-rewrite (frontmatter/file move/status carried) then a SINGLE batched rewrite_ids pass across all squad files + one _resync_edges; db.add each moved item. Audit per item: one reflog line (op='rename-type', delta old_id/new_id/old_type/new_type) and one system discussion comment, mirroring retype's trail (AC3).

Add a RenameResult dataclass to _services/_results.py (renamed count, per-item old->new id list, rewritten file names). Return it; the CLI (TASK-358) prints from it.

Files owned: src/squads/_services/_rename.py (new), src/squads/_services/_results.py (append RenameResult), src/squads/_services/_service.py (compose RenameMixin), src/squads/_index/_reflog.py (add 'rename-type' to the op-vocabulary docstring list only), tests/test_rename.py (new: service-level test). Do NOT touch _workflow/_models.py (read its existing surface only) to avoid colliding with FEAT-212.

Depends on TASK-355 (the extracted primitive).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 356 add-subtask "<title>"`; track with `sq task 356 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Bulk rename-type service under rename-specific validation | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Bulk rename-type service under rename-specific validation

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a project admin, I want sq migrate rename-type to safely rename a built-in type across my whole squad
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Added `RenameMixin.rename_type(old_type, new_type)` — a single-transaction bulk move of every item of one work type to another already-declared type, reusing the TASK-355 primitive with `carry_status=True`. Validation is fail-closed before any mutation (both types declared work types, non-reserved-meta, `old != new`, no child left with an invalid parent); sub-entities and status carry over unconditionally, and a snapshot/rollback layer keeps disk, index, and reflog byte-identical on any failure. Returns a `RenameResult`.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-10T00:49:53Z] Elias Python:
  - RenameMixin.rename_type(old_type, new_type) -> RenameResult in _services/_rename.py, composed into Service alongside RetypeMixin.
  - Validation (all before any mutation, inside the transaction but before the snapshot): both types declared + non-meta (spec.item_is_meta, clear 'reserved meta-type' message) via _validate_rename_types; old!=new; then _validate_no_invalid_children reuses spec.parent_allowed across every child of every renamed item at once.
  - Bulk mechanics: one store.transaction(), old_items sorted by sequence_id, per-item _apply_type_change(carry_status=True) building one combined remap, ONE rewrite_ids pass over every item's current path, ONE _resync_edges(remap, exclude=set()) -- deliberately NOT excluding renamed items, since same-type renamed items can ref each other and retype's single-pair exclude is a no-op that doesn't generalize to a multi-entry bulk remap.
  - Atomicity: added a snapshot/rollback layer in _rename.py (not touching _retype.py) -- every item's (path, text) is read once validation passes and before the first byte changes; any exception in the mutation phase restores every file to its original path+bytes before re-raising. The index itself is never written until the transaction body returns normally, so together this keeps disk+index byte-identical on both a validation failure and a genuine mid-flight failure (tested by monkeypatching _apply_type_change to raise on the 2nd item).
  - Audit: per renamed item, one reflog line (op=rename-type, delta old_id/new_id/old_type/new_type) + one system discussion comment mirroring retype's trail; added rename-type to the reflog docstring op list.
  - Gates green: pyright, ruff check, ruff format --check, test_rename.py (10 tests) + test_retype.py (all pass), test_squad_ref_hygiene.py. Full suite left to the main loop.
  - Reviewer should scrutinize: the exclude=set() deviation from the task's literal 'exclude=all renamed seqs' suggestion (I judged it incorrect for same-type cross-refs, see rationale above); the snapshot/rollback approach as a reasonable atomicity story built on top of TASK-355's eager-file-IO primitive without modifying _retype.py; and whether a zero-item rename (old_type has no live items) should be a no-op (current behavior) or an error.
  - Leaving InProgress for TASK-358 (CLI wiring) and review.
- [2026-07-10T00:57:00Z] Paul Reviewer:
  - Reviewed uncommitted TASK-356 diff (independent, high-risk atomicity focus). NOTE: _rename.py + test_rename.py are UNTRACKED (absent from git diff; read directly). VERDICT: APPROVE. Atomicity holds — validated by both code inspection and tests. gates clean (pyright/ruff/format), full suite green (exit 0, 0 failures).
  - ATOMICITY Q1 — snapshot covers ALL rewrite_ids-touched files: YES. _snapshot_files (_rename.py:65) iterates db.items.values() and captures (path,text) for every item file; rewrite_ids is driven with all_paths built from the SAME db.items.values() (_rename.py:145), so the snapshot set == the rewrite target set exactly. File-move undo is correct: _rollback_files (_rename.py:80) resolves each item's CURRENT path from the in-place-mutated db, renames new->orig when they differ, then restores orig bytes — moved files are moved back (no stray new file) and content-only edits (non-renamed ref-rewritten files) are restored. Rollback runs then re-raises (correct order).
  - ATOMICITY Q2 — rollback leaves reflog+index+disk clean: YES. store.transaction() defers _atomic_write (os.replace) AND the reflog flush to AFTER the yield, and _log only BUFFERS to ctx.reflog_ops — so a body exception writes neither .squads.json nor .reflog.jsonl; the in-memory ctx.db is discarded (next load re-reads disk). Disk .md is restored by _rollback_files. The mid-flight test asserts _snapshot_tree(squad_dir)==before, and squad_dir contains .squads.json + .reflog.jsonl + all .md, so it genuinely asserts all three axes byte-identical (not just one). Both validation-failure and mid-flight-failure paths verified clean.
  - ATOMICITY Q3 — exclude=set() is CORRECT: YES. _resync_edges(remap, exclude=set()) processes every item incl. the renamed ones, so a cross-ref between two same-type renamed items gets remapped (retype's single-pair exclude={own_seq} is safe only because a lone item can't ref itself; a multi-entry bulk remap has no such guarantee). No double-processing (rewrite_ids=disk, _resync_edges=memory, applied once each) and no self-ref bug (_remap_ref is idempotent by id-membership). test_rename_cross_refs_between_renamed_items_resynced is real and exercises exactly this.
- [2026-07-10T00:57:16Z] Paul Reviewer:
  - Q4 fail-closed: validation runs before the snapshot and before any write — undeclared new_type (not in spec.items), reserved meta (item_is_meta), old==new, and invalid-parent child all raise pre-mutation (t in items && not meta == spec.work_types() exactly, so the work-type check is covered). No id-collision risk: renames keep sequence_id, and the global counter (invariant #2) guarantees new_prefix-seq can't equal any existing id, and no remap key is also a value (old/new prefixes differ), so rewrite_ids has no chained-rewrite hazard. retype() untouched (_retype.py not in diff) — test_retype.py green in the full suite.
  - Q5 zero-item no-op: ACCEPTABLE as-is. Both types are validated as declared, so a typo errors; a real-but-empty type is a harmless no-op returning renamed=0/ids=[] (test_rename_no_items_is_a_noop). Leave it a no-op; the CLI (TASK-358) should surface the '0 renamed' count so an empty result is visible. No ticket IDs in source (grep clean).
  - Minor / non-blocking: (1) LOW test-strengthening — the mid-flight test injects failure BEFORE the batched rewrite_ids, so the highest-risk path (failure AFTER the whole-squad ref-rewrite, when non-renamed files are edited) isn't directly exercised; the code is correct by construction (snapshot==rewrite target set) but a fault injected at _append_rename_comment/_log would prove the post-rewrite rollback. (2) NIT — RenameResult.rewritten derives only from rewrite_ids 'touched', so a renamed item's file modified solely by the comment-append may be omitted from the reported list (cosmetic; CLI display only). (3) INFO — except Exception (not BaseException) means a SIGINT mid-flight skips file rollback, matching codebase convention; the index stays protected regardless. None block approval.
  - FEAT-281 progress: TASK-355 (primitive) + TASK-356 (bulk rename_type) both approved. rename_type is atomic across disk/index/reflog on every failure path I could construct; the O(N) seam from 355 is used correctly (one rewrite_ids + one _resync_edges). Safe to proceed to TASK-357 (rename-status) / TASK-358 (CLI wiring).
- [2026-07-10T00:59:51Z] Elias Python:
  - Added the requested post-rewrite rollback regression test: test_rename_failure_after_rewrite_ids_restores_everything in tests/test_rename.py. Monkeypatches _append_rename_comment to raise on the 2nd item, so the failure lands after rewrite_ids + _resync_edges have already touched every squad file (not before, like the existing mid-flight test); asserts _snapshot_tree(squad_dir) == before, which covers .squads.json + .reflog.jsonl + every .md file in one comparison.
  - Test-only change, no source edits. Gates: pyright/ruff check/ruff format --check clean; pytest tests/test_rename.py -q -> 11 passed; tests/test_squad_ref_hygiene.py -q -> 5 passed. Full suite not run per instructions. Still InProgress.
- [2026-07-10T01:03:03Z] Catherine Manager:
  - Reviewer-approved; atomicity confirmed on all three axes (index/reflog/filesystem) by both code inspection and tests. F1 (post-rewrite rollback not directly tested) fixed — added a failure-after-rewrite_ids test asserting full three-axis restore. F2 (RenameResult.rewritten omits comment-only-touched files) accepted as cosmetic WontFix; F3 (except Exception vs BaseException) matches codebase convention. Full suite green. Landing.
<!-- sq:discussion:end -->
