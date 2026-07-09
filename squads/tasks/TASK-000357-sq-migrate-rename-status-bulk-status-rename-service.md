---
id: TASK-357
sequence_id: 357
type: task
title: 'sq migrate rename-status: bulk status rename service'
status: Draft
parent: FEAT-281
author: tech-lead
subentities:
- local_id: ST1
  title: Bulk rename-status service scoped to the type's lifecycle
  status: Todo
  story: US2
created_at: '2026-07-09T21:34:35Z'
updated_at: '2026-07-09T21:36:01Z'
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
