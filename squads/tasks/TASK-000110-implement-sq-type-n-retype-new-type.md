---
id: TASK-000110
sequence_id: 110
type: task
title: Implement sq <type> <n> retype <new-type>
status: Done
parent: FEAT-000020
author: tech-lead
subentities:
- local_id: ST1
  title: 'Retype operation: flip type, move file, carry/reset status, refuse conflicts,
    system comment'
  status: Done
  story: US1
- local_id: ST2
  title: Rewrite all incoming edges (refs, children parent, prose mentions) to the
    new ID in one transaction
  status: Done
  story: US2
- local_id: ST3
  title: Wire the CLI verb + service tests, CLI smoke, workflow docs
  status: Done
  story: US1
created_at: '2026-06-15T08:20:30Z'
updated_at: '2026-06-15T08:46:33Z'
---
<!-- sq:body -->
## Goal

Add `sq <type> <n> retype <new-type>` — reclassify a work item in place, keeping its globally-unique number, body, discussion, and all incoming references. Work-item types only (epic, feature, task, bug, decision, review, guide). Joins the CLI grammar before the 1.0 freeze (EPIC-000012).

## Why this is one task

The number's identity is `Item.sequence_id` (stored); `Item.id` is a `@computed_field` from `type + sequence_id + id_padding`. So "retype" is literally **mutating the `type` field** — the prefix and ID flip for free, and the ref/parent/prose rewrite (US2) is the same atomic operation as the file move and status decision (US1). Splitting them would fracture a single index transaction, so US1 and US2 ship together; the subtasks carve the work, not separate transactions.

## Technical approach

New service method `retype(item_id, new_type)` (new mixin `src/squads/_services/_retype.py`, composed into the `Service` façade in `src/squads/_services/_service.py`), run inside one `store.transaction()`:

1. **Resolve + validate.** Load the item; reject if it is not a `WORK_TYPES` member or `new_type` is not (`src/squads/_models/_enums.py::WORK_TYPES`). No-op/refuse if `new_type == item.type`.
2. **Refusals (actionable errors, all `SquadsError`).**
   - Item has sub-entities (`item.subentities` non-empty) — refuse: retype loses the wrong-type container semantics. Hint to clear them first.
   - New parent invalid: `parent_allowed(new_type, parent.type)` is False — refuse with `parent_hint(new_type)` (`src/squads/_workflow.py`).
   - Any **child** whose `parent == item_id` would become invalid under the new type (e.g. retyping a feature→bug orphans its child tasks): scan `db.items` for children, check `parent_allowed(child.type, new_type)`, refuse listing the offenders.
3. **Status carry vs reset.** Compare `workflow_for(old)` and `workflow_for(new)` (`src/squads/_workflow.py`): if the same `Workflow` object **and** current status is in `new` workflow's `.states`, carry; otherwise reset to `initial_status(new_type)` and announce loudly in the result + system comment. (task↔bug, feature↔epic share `_WORK` so they carry; anything crossing into ADR/review/guide resets.)
4. **Flip type + move the file.** Set `item.type = new_type`. New filename `f"{item.id}-{item.slug}.md"` (id now reflects the new prefix), new folder `FOLDER_BY_TYPE[new_type]`. `old_path.rename(new_path)`; update `item.path` to the new `squad_relative`. Mirrors the rename mechanics in `_services/_items.py::_rename` and `_maintenance.py::_renumber`. **Body stays byte-verbatim** — only frontmatter is rewritten via `update_frontmatter` (`src/squads/_itemfile.py`).
5. **Append missing sub-entity container.** When retyping into feature/task/review and the body lacks the container marker (`SUBENTITY_CONTAINER` in `_services/_base.py`: stories/subtasks/findings + the summary table), append an empty container marker-safely via `_sections.py`. (Item is guaranteed to have no sub-entities by step 2, so the container is empty.)
6. **Rewrite all incoming edges (US2).** Build `remap = {OLD_ID: NEW_ID}` and call `rewrite_ids(all_item_paths, remap)` (`src/squads/_itemfile.py` — already does whole-word `\bOLD\b` substitution across frontmatter refs, `parent`, and inline prose mentions). Ref **kinds are preserved** automatically (they live as `ID:kind` and only the ID part matches). After the bulk rewrite, the in-memory `db` items must be re-synced for the children whose `parent` changed so the index matches disk — simplest: rewrite files then let the transaction's index reflect the retyped item, and rebuild affected parents' fields, or re-`load` post-rewrite. Verify `sq repair` is a no-op afterwards (invariant 1).
7. **System comment.** Append `retyped OLD → NEW` (and the status carry/reset note) to the item's `:discussion` via `discussion.format_comment` + `_sections.append_to_section` (author = an agent/operator slug, mirror `_services/_collab.py::comment`).

Return a result dataclass (new entry in `src/squads/_services/_results.py`) carrying old/new ID, carried-or-reset status, and the list of rewritten ref sources, so the CLI can state all three (Acceptance requires the output names them).

**CLI wiring (ST3):** add a `retype` verb in `src/squads/_cli/_items.py::build_item_app` (thin wrapper, like `_cmd_status`), taking the new type as an argument; resolve via the existing `_id(ctx)` + a type parser. Print new ID, carried/reset status, and rewritten-ref count. Document in the workflow cheatsheet partial `src/squads/_rendering/templates/workflow.md.j2` (shared by `sq workflow` and the `squads` skill).

## Files to touch

- NEW `src/squads/_services/_retype.py` — the `RetypeMixin.retype()` operation.
- `src/squads/_services/_service.py` — compose the new mixin into `Service`.
- `src/squads/_services/_results.py` — `RetypeResult` dataclass.
- `src/squads/_cli/_items.py` — register the `retype` verb.
- `src/squads/_rendering/templates/workflow.md.j2` — document the verb.
- Reuses (no edits expected): `_models/_enums.py` (WORK_TYPES, FOLDER_BY_TYPE), `_workflow.py` (workflow_for/parent_allowed/parent_hint/initial_status), `_itemfile.py` (rewrite_ids/update_frontmatter), `_services/_base.py` (SUBENTITY_CONTAINER), `_discussion.py`, `_sections.py`.
- Tests: `tests/` — service-level retype tests (every work-item pair; carry vs reset; all three refusal cases; refs/parent/prose rewrite; `sq check` clean + `sq repair` stable) + a CLI smoke test.

## Acceptance bar

- `sq <type> <n> retype <new-type>` works for every work-item pair; number, body, discussion, and refs survive; output states the new ID, carried/reset status, and rewritten refs.
- All three refusal cases error cleanly with next-step hints.
- After any retype: `sq check` clean, `sq repair` a stable no-op (proves frontmatter is the source of truth — invariant 1).
- pyright strict + ruff (check + format) green; covered by service tests + CLI smoke; documented in workflow docs.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 110 add-subtask "<title>"`; track with `sq task 110 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Retype operation: flip type, move file, carry/reset status, refuse conflicts, system comment | US1 |
| ST2 | Done |  | Rewrite all incoming edges (refs, children parent, prose mentions) to the new ID in one transaction | US2 |
| ST3 | Done |  | Wire the CLI verb + service tests, CLI smoke, workflow docs | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Retype operation: flip type, move file, carry/reset status, refuse conflicts, system comment

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a user who filed work under the wrong type, I want to retype it in place, so that the number, body and discussion survive the fix
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Core retype(item_id, new_type) in a new RetypeMixin: validate work-type→work-type; refuse on sub-entities present / invalid new parent / a child that would be orphaned; carry status when old and new share the _WORK workflow else reset to initial_status and announce; flip item.type, rename+move the file across folders, rewrite frontmatter only (body verbatim); append an empty sub-entity container when retyping into feature/task/review; write a 'retyped OLD → NEW' system comment. Files: src/squads/_services/_retype.py (new), _service.py, _results.py, _base.py (reuse SUBENTITY_CONTAINER), _itemfile.py, _discussion.py, _sections.py.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Rewrite all incoming edges (refs, children parent, prose mentions) to the new ID in one transaction

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a teammate whose items reference the retyped one, I want every incoming ref, parent link and prose mention rewritten to the new ID, so that nothing dangles
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
In the same transaction, build remap {OLD_ID: NEW_ID} and call rewrite_ids over every item file so other items' refs (kinds preserved via the ID:kind form), children's parent fields, and prose @-mentions all flip to the new ID. Re-sync affected in-memory items so the index matches disk; assert sq check clean and sq repair a no-op afterwards. Files: src/squads/_itemfile.py (rewrite_ids — reuse), src/squads/_services/_retype.py.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Wire the CLI verb + service tests, CLI smoke, workflow docs

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a user who filed work under the wrong type, I want to retype it in place, so that the number, body and discussion survive the fix
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Register the retype verb in build_item_app (thin wrapper over svc.retype, type-argument parser, prints new ID + carried/reset status + rewritten-ref count); add service tests across all work-item pairs + carry/reset + the three refusals + ref/parent/prose rewrite + check/repair stability, plus a CLI smoke test; document the verb in workflow.md.j2. Files: src/squads/_cli/_items.py, src/squads/_rendering/templates/workflow.md.j2, tests/.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-15T08:38:13Z] Elias Python:
  - Implemented TASK-110: sq retype in place.
    
    New files: src/squads/_services/_retype.py (RetypeMixin with retype()), src/squads/_rendering/templates_manifest.json updated, tests/test_retype.py (33 tests).
    
    Changes: _service.py composes RetypeMixin, _results.py already had RetypeResult, _cli/_items.py adds _cmd_retype verb + WORK_TYPES import + parse_type import, workflow.md.j2 documents the retype section.
    
    All three refusals (sub-entities, invalid new parent, invalid children) error cleanly. Status carries on same-workflow pairs (task↔bug, feature↔epic), resets otherwise. All incoming edges (refs with kinds preserved, children's parent, prose mentions) rewritten atomically in one transaction. System comment appended to discussion. Sub-entity container scaffolded when retyping into feature/task/review.
    
    Gate: 635 passed, 0 failed; pyright 0 errors; ruff check + format clean.
    
    @reviewer please review the implementation. @qa please smoke test retype across all work-item pairs.
- [2026-06-15T08:43:30Z] Mara Tester:
  - QA verification of FEAT-000020 (Retype an item in place) — empirical checks in a scratch squad + full test suite.
  - **Core retype (US1/AC1):** PASS — sq task N retype bug: sequence number preserved, ID reprefixes (TASK-000002 → BUG-000002), file moves to bugs/, body byte-for-byte verbatim (Unicode: ← → ✓ intact), frontmatter updated, output states old/new ID.
  - **Incoming edges (US2/AC1):** PASS — refs in other items rewritten to new ID; ref kind preserved (blocks); prose @-mentions and inline IDs rewritten; children's parent field rewritten; sq check clean after retype.
  - **Status carry:** PASS — feature→epic (shared _WORK workflow) carries Ready status; task→bug carries InProgress; output: 'status carried: <Status>'.
  - **Status reset:** PASS — task→decision resets to Proposed; task→guide resets to Draft; output: 'status reset: InProgress → Proposed (workflows differ)'; system comment records it.
  - **Refusals:** PASS — (1) item has sub-entities: 'cannot retype … it has sub-entities'; (2) parent invalid for new type: actionable message with parent_hint; (3) child would be orphaned: 'child item(s) … would have an invalid parent type'. All exit 1 with next-step hints.
  - **Invariant 1 (sq repair):** PASS — sq repair after retype reports no missing IDs, counter consistent; sq check clean.
  - **System comment:** PASS — discussion section records 'retyped OLD → NEW; status carried/reset as <Status>'.
  - **Workflow docs:** PASS — sq workflow output shows retype verb, example, and post-retype invariant note.
  - **Static analysis:** PASS — pyright strict: 0 errors; ruff check: all passed; ruff format --check: 98 files formatted.
  - **Full test suite:** PASS — 635 passed, 1 skipped (all 33 retype tests green).
  - **Minor gap noted:** when no refs are rewritten, the CLI omits the '0 file(s)' line from output. Spec says output 'states … rewritten refs' but omitting a zero count is reasonable — not blocking.
- [2026-06-15T08:45:29Z] Paul Reviewer:
  - Reviewed in REV-000115: APPROVED. Retype is correct end-to-end — sequence number preserved, ID reprefixes via the computed field, file moved to the new folder with body bytes verbatim and markers intact; incoming edges (refs with kinds, children's parent, prose mentions) rewritten atomically in one transaction with no dangling refs; status carry-vs-reset correct per workflow; all three refusals fire with actionable hints.
  - Invariant 1 verified hands-on: after a retype with a ref + prose rewrite, sq check is clean and sq repair rebuilds the index byte-identically from frontmatter. Forward-edges-only, marker-safe edits, injectable clock, and e() escaping all respected.
  - Architect-flagged forward reference (_cmd_retype call-before-def in _cli/_items.py): genuinely resolved — build_item_app only runs from _cli/__init__.py after the module loads, so the name binds at call time. Not masked.
  - Gate green: 635 passed / 1 skipped, pyright 0 errors, ruff check + format clean.
  - Two LOW-severity, non-blocking quality findings (F1, F2 in REV-000115) — optional cleanup, not required to ship: F1 an avoidable '# type: ignore[assignment]' from typing current_status as object in _carry_or_reset_status; F2 a duplicated subentity-kind reverse map that already exists as _base.SUBENTITY_KIND. @python-dev your call whether to fold these in now or leave them.
<!-- sq:discussion:end -->
