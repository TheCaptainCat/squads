---
id: TASK-304
sequence_id: 304
type: task
title: 'Sharpen sq-feature skill: story-body write as ordered DoD step'
status: Done
parent: FEAT-289
author: tech-lead
assignee: python-dev
description: Split body-writing into its own PO Do step + Watch-for DoD line in playbook.toml;
  regen via sq sync
subentities:
- local_id: ST1
  title: Split story-body write into its own PO Do step in playbook.toml
  status: Done
  story: US3
- local_id: ST2
  title: Add the Watch-for DoD line + regen skill via sq sync
  status: Done
  story: US3
created_at: '2026-07-06T11:37:24Z'
updated_at: '2026-07-06T12:10:01Z'
---
<!-- sq:body -->
Sharpen the generated `sq-feature` skill so a product owner treats writing a story's body as its own ordered step and a definition-of-done, not a parenthetical. Covers FEAT-289 US3.

Source of truth: `src/squads/_interactions/playbook.toml` -> `[types.feature]` -> the `[[types.feature.roles]]` block with `slug = "product-owner"`. Today the body-writing guidance is folded into the add-story 'Do' bullet's parenthetical ('… acceptance criteria and detail go in the story body …'). This is a MANAGED-SKILL change: edit the playbook source and regenerate via `sq sync`; never hand-edit the on-disk `squads/agents/skills/SKILL-000196-sq-feature.md`.

Done when: the PO 'Do' list has writing the story body as its own distinct ordered bullet (separate from 'add persona-worded user stories'); 'Watch for' gains a DoD line: 'a story is not done until its body carries acceptance criteria — an unwritten placeholder body is a defect even if the title reads fine.'; `sq sync` regenerates the on-disk skill and the diff shows the new step + watch line; pyright/ruff/tests clean (skill-content assertions if any).

Scope note: the sibling `[types.task]` python-dev/tech-lead guidance has the same soft-gap for the subtask body (line ~121, body folded into a parenthetical). That extension is a fast-follow and is OUT OF SCOPE here — just note it; do not change it in this task.

No sq/FEAT IDs in the shipped skill text or source; referencing FEAT-289/US3 in this task body is fine.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 304 add-subtask "<title>"`; track with `sq task 304 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Split story-body write into its own PO Do step in playbook.toml | US3 |
| ST2 | Done |  | Add the Watch-for DoD line + regen skill via sq sync | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Split story-body write into its own PO Do step in playbook.toml

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a PO, I want the skill to state the body-write step as a done-criterion
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Done when: in `playbook.toml` under the feature product-owner role, the add-story 'Do' bullet no longer carries the body-writing guidance as a parenthetical, and a new standalone 'Do' bullet (ordered after add-story) instructs the PO to write each story's body with `sq feature <n> story <k> body -m …`, stating that acceptance criteria live there. The add-story bullet keeps only the title/persona-phrase guidance.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Add the Watch-for DoD line + regen skill via sq sync

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a PO, I want the skill to state the body-write step as a done-criterion
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Done when: the feature product-owner 'Watch for' list gains the DoD line 'a story is not done until its body carries acceptance criteria — an unwritten placeholder body is a defect even if the title reads fine.', and `sq sync` regenerates `SKILL-000196-sq-feature.md` on disk so the new Do step + Watch-for line appear there (verified by diff, not by hand-editing the generated file).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-06T11:44:59Z] Elias Python:
  - Split the add-story 'Do' bullet in src/squads/_interactions/playbook.toml [[types.feature.roles]] (product-owner): the body-writing guidance is now its own ordered bullet ('write each story's body ... the acceptance criteria live there, not in the title'), separate from the add-story bullet (title/persona-phrase only).
  - Added the Watch-for DoD line: 'a story is not done until its body carries acceptance criteria — an unwritten placeholder body is a defect even if the title reads fine.'
  - Ran uv run sq sync: regenerated squads/agents/skills/SKILL-000196-sq-feature.md — diff shows exactly the new Do step + Watch-for line, nothing else.
  - Scope note (fast-follow, not done here): [types.task] tech-lead subtask-body guidance has the same parenthetical soft-gap around line ~121 of playbook.toml.
<!-- sq:discussion:end -->
