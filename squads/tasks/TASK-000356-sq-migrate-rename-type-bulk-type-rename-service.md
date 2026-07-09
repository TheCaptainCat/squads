---
id: TASK-356
sequence_id: 356
type: task
title: 'sq migrate rename-type: bulk type rename service'
status: Draft
parent: FEAT-281
author: tech-lead
subentities:
- local_id: ST1
  title: Bulk rename-type service under rename-specific validation
  status: Todo
  story: US1
created_at: '2026-07-09T21:34:34Z'
updated_at: '2026-07-09T21:36:01Z'
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
