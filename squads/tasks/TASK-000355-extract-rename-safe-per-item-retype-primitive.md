---
id: TASK-355
sequence_id: 355
type: task
title: Extract rename-safe per-item retype primitive
status: Draft
parent: FEAT-281
author: tech-lead
subentities:
- local_id: ST1
  title: Extract reusable per-item type-rewrite primitive from retype()
  status: Todo
  story: US1
created_at: '2026-07-09T21:34:34Z'
updated_at: '2026-07-09T21:36:00Z'
---
<!-- sq:body -->
Enabler for rename-type (TASK-356). Refactor _services/_retype.py so the per-item rewrite sequence inside retype() becomes a reusable primitive that the bulk rename path can call without retype()'s single-item reclassification guardrails.

Extract the mutate-one-item core (currently inline in RetypeMixin.retype, lines ~135-174) into a module-level async helper, e.g. _apply_type_change(db, item, new_type, *, carry_status: bool). It must: stamp prefix_for(new_type, spec), recompute the unpadded id, move the file (padded stem via format_item_id), update frontmatter, ensure the sub-entity container, and bump updated_at. Status handling becomes a parameter: retype() keeps its carry-or-reset via _carry_or_reset_status; the rename caller passes carry_status=True (carry unconditionally).

Separate the two seams so the bulk path stays O(N), not O(N^2): (a) per-item self-rewrite (frontmatter/file/status) and (b) a batchable edge remap. Today retype() calls rewrite_ids over all squad files once per item; the rename path must build ONE combined {old_id:new_id} remap across every renamed item and do a single rewrite_ids pass, then one _resync_edges pass. Factor the edge-rewrite so both a single {old:new} (retype) and a bulk dict (rename) work through the same code.

Keep the reflog+comment emitters reusable: _append_retype_comment and the store._log('retype', ...) call should be parameterizable enough that rename can emit its own op/message per item (see TASK-356/357). Either generalize them (op arg, message builder) or leave them retype-specific and have rename supply its own — dev's call, note it in the PR.

HARD CONSTRAINT: retype() behaviour and its audit trail (reflog line + discussion comment) must be byte-identical after the refactor. This is a pure extraction — no functional change. tests/test_retype.py must pass unchanged.

Files owned: src/squads/_services/_retype.py; tests/test_retype.py (only if the extraction needs new unit coverage of the primitive — do not weaken existing assertions). Do NOT touch _workflow/_models.py.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 355 add-subtask "<title>"`; track with `sq task 355 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Extract reusable per-item type-rewrite primitive from retype() | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Extract reusable per-item type-rewrite primitive from retype()

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a project admin, I want sq migrate rename-type to safely rename a built-in type across my whole squad
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
