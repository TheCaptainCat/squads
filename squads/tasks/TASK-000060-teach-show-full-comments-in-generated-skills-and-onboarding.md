---
id: TASK-000060
sequence_id: 60
type: task
title: Teach show --full --comments in generated skills and onboarding (US6)
status: Done
parent: FEAT-000026
author: tech-lead
assignee: python-dev
priority: high
subentities:
- local_id: ST1
  title: Teach --full --comments in generated skills and onboarding
  status: Done
  story: US6
created_at: '2026-06-12T08:58:27Z'
updated_at: '2026-06-12T09:27:15Z'
---
<!-- sq:body -->
## Goal

Close the guidance gap (US6): once `--full` and `--comments` exist, the generated `squads` skill and every per-type `sq-<type>` skill teach reading with `show --full --comments` as the standard briefing move — so an agent following only the generated skills automatically reads the full dossier, including decisions captured only in discussion comments. The incident that motivated this (an agent briefed from the body and missed the flag semantics recorded only in comments) must be closed.

## In scope

- Per-type `sq-<type>` skills: the **Enter** / "before you act" checklist of each must instruct reading the item with `show --full --comments`. These are data-driven from the playbook, NOT hand-edited markdown — update the `enter` tuples in src/squads/_interactions.py (and any shared default) so every type's Enter section surfaces the flags. Verify the rendered item_skill output carries it.
- The generated `squads` skill: its reading guidance must recommend `sq <type> <n> show --full --comments` for briefing, not just plain `show`. Update src/squads/_rendering/templates/agents/squads_skill.md.j2 (the `show` lines around the "details + body" example and the "Anchor to an item" guidance).
- Any other generated text teaching `sq <type> <n> show`: the item_skill footer (item_skill.md.j2 line ~55 "Read anything back with sq <type> <n> show"), workflow docs (_rendering/templates/workflow.md.j2), and role onboarding — sweep them so the flags are surfaced consistently.
- Requirement is **replayable** and present in generated output of `sq sync` / `sq backend sync` — not just handwritten notes. After changes, run `sq sync` and confirm the generated skills under squads/agents/skills/ carry the guidance.

## Anchors

- src/squads/_interactions.py — the `enter`/`do`/`watch` tuples per role x item type; `*dev` sentinel = any tech-dev. This is what fills each sq-<type> skill's Enter section via item_skill.md.j2.
- src/squads/_rendering/templates/agents/item_skill.md.j2 — Enter section render (line ~22) + footer "Read anything back" (line ~55).
- src/squads/_rendering/templates/agents/squads_skill.md.j2 — the show examples (lines ~22, ~36, ~57).
- src/squads/_rendering/templates/workflow.md.j2 — workflow cheatsheet (shared by squads skill + sq workflow).

## Sequencing

Gated behind TASK-000058 + TASK-000059 — the flags must exist before the docs teach them. Pure docs/templates; no overlap with the renderer files.

## Tests

Assert the generated skill text contains the `--full --comments` guidance (a rendering test on item_skill / squads_skill output, and/or a check on the synced files). Keep existing skill-generation tests green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 60 add-subtask "<title>"`; track with `sq task 60 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Teach --full --comments in generated skills and onboarding | US6 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Teach --full --comments in generated skills and onboarding

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US6 — As an agent briefing on an item, I want the squads skill and the sq-<type> skills to teach reading with --full --comments as the standard briefing move, so that decisions captured in discussion comments are never missed
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
- [2026-06-12T09:27:12Z] Elias Python:
  - TASK-000060 complete. All gates green (333 passed, pyright + ruff clean).
  - Single-source for the briefing guidance: item_skill.md.j2 now injects a universal first Enter bullet — 'Read the full item dossier: `sq \<type\> \<n\> show --full --comments`' — into every role section of every per-type sq-\<type\> skill. No changes to _interactions.py were needed; the template is the right single point.
  - squads_skill.md.j2: updated three locations — Golden rules sub-entity read line, Anchor-to-an-item guidance (now explicitly names --full --comments), and the Common commands show example.
  - workflow.md.j2: updated the 'read back with show' bullet in the Team workflow section.
  - claude_section.md.j2: updated the Orchestration loop 'brief on one item' line and the Working with squads 'Read with show' line.
  - sq sync run — all generated files under squads/agents/skills/ carry the guidance. Verified with grep: every sq-\*.md has at least 3 occurrences of '--full --comments'.
  - New tests in tests/test_skills.py: test_squads_skill_teaches_full_comments_briefing (checks the squads skill body) and test_item_skills_teach_full_comments_briefing (checks every managed item type's generated skill).
<!-- sq:discussion:end -->
