---
id: TASK-357
sequence_id: 357
type: task
title: 'sq migrate rename-status: bulk status rename service'
status: Done
parent: FEAT-281
author: tech-lead
subentities:
- local_id: ST1
  title: Bulk rename-status service scoped to the type's lifecycle
  status: Todo
  story: US2
created_at: '2026-07-09T21:34:35Z'
updated_at: '2026-07-13T09:27:36Z'
---
<!-- sq:body -->
Implements US2. Add rename_status(type, old_status, new_status) to RenameMixin (src/squads/_services/_rename.py, the module created in TASK-356): bulk-moves every item of <type> currently at <old-status> to <new-status> in one transaction.

Per-type by construction (re-baseline #3): status names are GLOBAL vocabulary shared across lifecycles, so the rename is scoped to one type's own machine and only that type's items — never a spec-wide status rename. Validate new_status membership in spec.workflow_for(type).states (a valid STATE, not a valid can_transition edge — this is a relabel, not a workflow move). Terminal/open classification and any completion badge are inherited from whatever new_status already declares; the migration only moves the status: value.

Validation, fail-closed with no partial rewrite: <type> is a work type and not a reserved meta-type (role/skill/operator); new_status resolves in that type's states. On failure raise SquadsError before mutating anything.

Mechanics: ONE transaction; for every item where item.type==type and item.status==old_status set item.status=new_status and bump updated_at; db.add. No IDs, files, or folders change (a status rename is frontmatter-only). Note: only the TOP-LEVEL item status is renamed — sub-entity status vocabulary is the FEAT-212/ADR-348 axis and is explicitly out of scope; do not touch Item.subentities. Audit per item: reflog line op='rename-status' (delta type/old/new) + system discussion comment, mirroring retype (AC3). Reuse the RenameResult from TASK-356.

Files owned: src/squads/_services/_rename.py (add the method), src/squads/_index/_reflog.py (add 'rename-status' to the op-vocabulary docstring), tests/test_rename.py (add status cases). Do NOT touch _workflow/_models.py.

Depends on TASK-356 (shares the RenameMixin module + RenameResult; sequenced after it to avoid same-file collision).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 357 add-subtask "<title>"`; track with `sq task 357 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Bulk rename-status service scoped to the type's lifecycle | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Bulk rename-status service scoped to the type's lifecycle

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US2 — As a project admin, I want sq migrate rename-status to safely rename a status across all items of a type
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Added `RenameMixin.rename_status(type, old_status, new_status)` — a single-transaction, frontmatter-only relabel of every item of one type currently at a given status, scoped per-type (status names are global vocabulary, so only that type's items are touched). `new_status` is validated as a member of that type's lifecycle states (a relabel, not a workflow move), `Item.subentities` is left untouched, and it reuses TASK-356's `RenameResult` plus the snapshot/rollback atomicity.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-10T01:09:07Z] Elias Python:
  - Implemented RenameMixin.rename_status(item_type, old_status, new_status) in _services/_rename.py, reusing TASK-356's RenameResult + _snapshot_files/_rollback_files atomicity helpers.
  - Per-type scoping: item_type must be a declared non-meta work type (mirrors rename_type's own validation, distinct message for undeclared vs reserved meta-type); new_status is validated as a member of spec.workflow_for(item_type).states — a STATE membership check, not can_transition, so it's a pure relabel.
  - Mechanics: one transaction; filters db.items by (type==item_type and status==old_status), sets status + bumps updated_at + update_frontmatter + db.add per matching item, frontmatter-only (no id/file/folder change). Item.subentities never touched — added test_rename_status_leaves_subentities_untouched to prove it.
  - Atomicity: snapshot taken after validation, before first write; on any exception in the mutation loop, _rollback_files restores every squad file, then re-raises. Added test_rename_status_mid_flight_failure_restores_disk_and_index asserting full _snapshot_tree equality, same pattern as rename_type's test.
  - Audit: reflog op='rename-status' (delta: type/old_status/new_status) + system discussion comment per item; added 'rename-status' to the _reflog.py op-vocabulary docstring.
  - Fast gates green: pyright, ruff check, ruff format --check; tests/test_rename.py + tests/test_retype.py + tests/test_squad_ref_hygiene.py all pass. Did not run the full suite (left to the main loop).
  - Left InProgress for review/CLI wiring (TASK-358). Reviewer: worth a second look at RenameResult.ids carrying (item.id, item.id) pairs since the id never changes for a status rename — kept it for RenameResult-shape reuse rather than adding a new result type; also confirm the per-type validation message split (undeclared vs reserved meta-type vs non-member new_status) reads clearly for CLI error surfacing.
- [2026-07-10T01:13:36Z] Paul Reviewer:
  - Reviewed uncommitted TASK-357 diff (independent, sibling of the approved rename_type). VERDICT: APPROVE. All four focus axes verified yes; gates clean (pyright/ruff/format), full suite green (exit 0, 0 failures); no ticket IDs in source.
  - Per-type scoping (Q1): YES. matching = items where it.type==item_type AND it.status==old_status (_rename.py:220), and validation resolves against spec.workflow_for(item_type).states only — never spec-wide. An item of a different type sharing the status name is untouched; test_rename_status_scoped_to_one_type proves a bug at 'InProgress' survives a task-scoped rename.
  - State-membership validation (Q2): YES. _validate_rename_status (_rename.py:65) checks new_status in spec.workflow_for(item_type).states (membership), NOT can_transition — a relabel, not a workflow move. Only item.status is reassigned; terminal/open/completion classification is resolved from new_status's own StatusSpec at read time (nothing classification-related is stored on the item), so it's inherited correctly. old_status isn't validated, which is fine — a non-member old_status yields 0 matches (no-op), consistent with the zero-item path.
  - Atomicity (Q3): YES, same three-axis discipline as rename_type. Reuses _snapshot_files (all item files) + try/except->_rollback_files->raise inside store.transaction(); eager writes are only update_frontmatter + the comment append (both snapshotted); no rewrite_ids (ids unchanged) so no file moves — rollback is pure byte-restore. Transaction defers os.replace and buffers the reflog, so a body exception persists neither index nor reflog. test_rename_status_mid_flight_failure injects at the 2nd _append_rename_status_comment (AFTER item 1's frontmatter+comment hit disk) and asserts _snapshot_tree(squad_dir)==before — and squad_dir holds .squads.json + .reflog.jsonl + all .md, so it genuinely asserts all three axes.
  - Sub-entities untouched (Q4): YES. The loop sets only item.status + item.updated_at; Item.subentities is never read or mutated (update_frontmatter round-trips it verbatim). test_rename_status_leaves_subentities_untouched confirms the subtask status is preserved.
  - Fail-closed (Q5): YES — _validate_rename_status runs before the snapshot/any write (undeclared type, reserved meta, non-member new_status), each with a tree-unchanged test. Q6 (ids=(id,id)): acceptable as-is per the task's 'reuse RenameResult' instruction — a status rename never changes the id, so both slots equal. Forward-note for TASK-358: don't render the ids as 'old -> new' for rename_status (it'd print 'TASK-5 -> TASK-5'); print the count + status transition instead. Benign dataclass reuse, not a defect here.
- [2026-07-10T01:14:13Z] Catherine Manager:
  - Reviewer-approved, no blocking findings. Per-type scoping (status is global vocab, rename touches only that type's items), state-membership validation, three-axis atomicity (reused 356's snapshot/rollback), and sub-entities-untouched all confirmed. Full suite green. Forward-note carried to TASK-358: render status renames as count + status transition, not old→new ids (RenameResult.ids is (id,id) for status). Landing.
<!-- sq:discussion:end -->
