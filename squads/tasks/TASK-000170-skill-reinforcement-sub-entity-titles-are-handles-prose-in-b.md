---
id: TASK-000170
sequence_id: 170
type: task
title: 'Skill reinforcement: sub-entity titles are handles, prose in body'
status: Done
parent: FEAT-000166
author: tech-lead
refs:
- ADR-000167
subentities:
- local_id: ST1
  title: Add handle-vs-body note to sq-review add-finding guidance
  status: Done
  story: US3
- local_id: ST2
  title: Add handle-vs-body note to sq-task add-subtask guidance
  status: Done
  story: US3
- local_id: ST3
  title: Add handle-vs-body note to sq-feature add-story guidance
  status: Done
  story: US3
created_at: '2026-06-23T08:37:43Z'
updated_at: '2026-06-23T09:30:07Z'
---
<!-- sq:body -->
Update the sq-review / sq-task / sq-feature skill generation templates to state that a sub-entity title is a short one-line handle and the spec/description belongs in the body. Implements US3.

## Design (per ADR-000167)
- Content/template change only — no runtime code. Edit the skill generation templates so the guidance regenerates via sq sync with no manual edits.
- Each note is concise (one or two sentences) and placed near the relevant add-* command in its skill.

## What each skill must say
- sq-review (near add-finding): the finding title is a short handle; the full finding description goes in the finding body.
- sq-task (near add-subtask): the subtask title is a short handle; implementation detail goes in the subtask body.
- sq-feature (near add-story): the story title is the short user-story phrase; acceptance criteria and detail go in the story body.

## Acceptance criteria
- All three skills carry the explicit handle-vs-body note near the relevant command, per the wording above.
- Notes are concise (1–2 sentences).
- Skills regenerate cleanly via sq sync with no manual edits required (the change lives in the templates / interactions content, not hand-edited managed files).

## Tests
- Regenerate and assert the note text appears in each generated skill; confirm sq sync is idempotent (no diff on a second run).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 170 add-subtask "<title>"`; track with `sq task 170 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Add handle-vs-body note to sq-review add-finding guidance | US3 |
| ST2 | Done |  | Add handle-vs-body note to sq-task add-subtask guidance | US3 |
| ST3 | Done |  | Add handle-vs-body note to sq-feature add-story guidance | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add handle-vs-body note to sq-review add-finding guidance

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US3 — As any agent, I want the sq-review / sq-task / sq-feature skills to tell me titles are handles
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
In the sq-review skill template, near the add-finding guidance, add a concise (1–2 sentence) note: the finding title is a short one-line handle; the full finding description goes in the finding body. Must regenerate via sq sync with no manual edits.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Add handle-vs-body note to sq-task add-subtask guidance

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US3 — As any agent, I want the sq-review / sq-task / sq-feature skills to tell me titles are handles
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
In the sq-task skill template, near the add-subtask guidance, add a concise (1–2 sentence) note: the subtask title is a short handle; implementation detail goes in the subtask body. Must regenerate via sq sync with no manual edits.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Add handle-vs-body note to sq-feature add-story guidance

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US3 — As any agent, I want the sq-review / sq-task / sq-feature skills to tell me titles are handles
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
In the sq-feature skill template, near the add-story guidance, add a concise (1–2 sentence) note: the story title is the short user-story phrase; acceptance criteria and detail go in the story body. Must regenerate via sq sync with no manual edits. Verify sq sync is idempotent across all three skills (no diff on a second run).
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-23T08:59:33Z] Theo Writer:
  - Skill reinforcement complete: Updated PLAYBOOK in src/squads/_interactions.py to add handle-vs-body notes to the product-owner (add-story), tech-lead (add-subtask), and reviewer (add-finding) guidance sections. Generated skills (sq-feature, sq-task, sq-review) now carry the concise 1-2 sentence notes per spec. Verified with sq sync idempotency test (second run produced no changes). Added test_item_skills_teach_handle_vs_body_note to tests/test_skills.py to assert the notes appear in all three generated skills. All tests passing, code style clean (pyright/ruff).
- [2026-06-23T09:30:07Z] Paul Reviewer:
  - Reviewed in REV-000173 — APPROVED, no findings. Notes are in the PLAYBOOK source (not hand-edited), sq sync is idempotent (zero churn on re-run, per ST3), all three skills carry clear in-voice handle-vs-body notes, and the added test genuinely guards them. Markers intact, style clean.
<!-- sq:discussion:end -->
