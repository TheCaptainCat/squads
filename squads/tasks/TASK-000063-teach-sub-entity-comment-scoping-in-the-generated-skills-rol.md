---
id: TASK-63
sequence_id: 63
type: task
title: Teach sub-entity comment scoping in the generated skills + role templates
status: Done
parent: FEAT-62
author: tech-lead
assignee: python-dev
priority: medium
subentities:
- local_id: ST1
  title: State the scoping convention once in squads_skill.md.j2
  status: Done
  story: US1
- local_id: ST2
  title: Add role-specific scoped-comment guidance in _interactions.py
  status: Done
  story: US2
- local_id: ST3
  title: 'Tests: scoping convention in skills/roles + @mention inbox no-regression'
  status: Done
  story: US3
created_at: '2026-06-12T09:55:14Z'
updated_at: '2026-06-23T09:58:09Z'
---
<!-- sq:body -->
**Goal.** Teach agents the comment-scoping convention — sub-entity discussions for scoped material, the main item discussion for cross-cutting material — across the generated skills and role templates. Content/template only — NO CLI behaviour changes, no parsing or inbox changes (the inbox already surfaces sub-entity @mentions; the PO verified this empirically 2026-06-12). The convention is preference-based guidance, not a hard rule.

**The convention to ship (from FEAT-62 body — read it for the full wording).**
- _Sub-entity discussion_ (`sq <type> <n> <kind> <k> comment`) for anything scoped to one story/subtask/finding: finding fix rationale, reproduction and verification notes, "agreed, closing this one"; story acceptance clarifications, story-local blockers/questions; subtask implementation notes and sub-assignee check-ins.
- _Main item discussion_ (`sq <type> <n> comment`) for cross-cutting material: handoff @mentions that announce a transition or request action from the next agent, decisions affecting more than one sub-entity or the whole item, item-level status summaries.
- @mentions are picked up by the inbox wherever they live, so they may go in the scope that fits — prefer the main discussion for handoff/transition mentions, the sub-entity for a scoped question (e.g. "F2 — @reviewer does this fix satisfy the requirement?").

**Single source of the convention text.** State the convention ONCE in the `squads` skill template (`src/squads/_rendering/templates/agents/squads_skill.md.j2`), in the "Hand back through sq" / "Working directly with the operator" area — that is the one skill every agent loads. Mirror how TASK-53 handled the regime principle: one formulation, everything else references it. The per-type skill role lines and the role template add a short pointer ("scope your comment per the squads skill's comment-scoping convention") plus at most one role-specific example — they do NOT restate the full convention. No drift.

**Surfaces (regenerated via `sq sync`, not migrated):**
1. `squads_skill.md.j2` — add the canonical convention paragraph (the single source). Cover all three sub-entity types with one concrete example each (finding rationale, story acceptance note, subtask implementation note).
2. `src/squads/_interactions.py` — the per-role enter/do/handoff lines that feed the "For X" sections of the per-type skills. Add scoped-comment guidance to: REVIEW reviewer + dev (finding-scoped comments when closing/responding to a finding), FEATURE product-owner + tech-lead (story-scoped comments for acceptance clarification), TASK dev (subtask-scoped implementation notes). Each line points at the squads-skill convention rather than restating it; keep every @mention a real call-to-action.
3. `src/squads/_rendering/templates/agents/role.md.j2` — working agreements: one brief sentence naming the scoping principle and pointing at the squads skill, so it is visible when an agent loads its role. Both regimes (spawned + live) inherit it.

**Confirm single-source discipline.** The full convention wording lives only in the squads skill; everywhere else is a reference + optional one-line example. If a surface seems to need its own full restatement, that is a flag to raise, not to duplicate.

**Regeneration check.** A clean `uv run sq sync` must propagate the new text to every managed skill pointer + the project's own `squads/agents/skills/*.md` and `squads/agents/roles/*.md`. No schema migration. Markers stay intact.

**Tests.** Extend `tests/test_skills.py` / `tests/test_rendering.py`: assert the generated `squads` skill contains the convention and a sub-entity comment example; assert the generated `sq-review`/`sq-feature`/`sq-task` skills carry the role-specific scoped-comment guidance; assert a generated role file names the scoping principle; assert markers stay intact. Add the no-regression inbox assertion (a sub-entity comment containing an @mention is surfaced by `sq inbox <role>`) if not already covered. Keep pyright + ruff clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 63 add-subtask "<title>"`; track with `sq task 63 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | State the scoping convention once in squads_skill.md.j2 | US1 |
| ST2 | Done |  | Add role-specific scoped-comment guidance in _interactions.py | US2 |
| ST3 | Done |  | Tests: scoping convention in skills/roles + @mention inbox no-regression | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — State the scoping convention once in squads_skill.md.j2

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As an agent writing a comment, I want the skills I load to tell me whether to use `sq <type> <n> <kind> <k> comment` or `sq <type> <n> comment`, so that I never route fix rationale or acceptance notes to the wrong discussion
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
State the convention once in squads_skill.md.j2 (single source): sub-entity command for scoped material, main command for cross-cutting, with one example per sub-entity type; add the brief scoping-principle sentence + reference to role.md.j2 working agreements (both regimes).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-06-12T09:59:16Z] Elias Python:
  - Added comment-scoping convention block to squads_skill.md.j2 under the Hand-back-through-sq bullet (single-source location). Convention covers all three sub-entity kinds with a table (finding/story/subtask examples) plus the inbox rule on @mention placement.
  - Added one-sentence pointer to role.md.j2 working-agreements: names the sub-entity-scoped command shape, the main-discussion default, and references the squads skill convention by name.
  - sq sync run — all role and skill files regenerated; sq check clean.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Add role-specific scoped-comment guidance in _interactions.py

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — As an agent reading a dossier with `--full --comments`, I want each sub-entity pane to contain the discussion that is scoped to it, so that I can brief on a finding or story without hunting through the parent item's main discussion
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Add role-specific scoped-comment guidance to the per-role lines in _interactions.py — REVIEW reviewer/dev (finding-scoped), FEATURE po/tech-lead (story-scoped), TASK dev (subtask-scoped) — each pointing at the squads-skill convention, not restating it; verify sq sync regenerates every skill + role file with markers intact.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-06-12T09:59:27Z] Elias Python:
  - Updated _interactions.py with role-specific scoped-comment guidance: REVIEW reviewer (use finding <k> comment for rationale/verification, main discussion for cross-cutting verdict), REVIEW dev (finding <k> comment when closing with rationale), FEATURE product-owner (story <k> comment for acceptance clarifications), FEATURE tech-lead (story <k> comment for story questions), TASK dev (subtask <k> comment for implementation notes, task comment for handoffs).
  - Each line points at the squads skill convention by name — no restatement. sq sync clean, sq check clean.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Tests: scoping convention in skills/roles + @mention inbox no-regression

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US3 — As an agent reading my inbox, I want @mentions placed in sub-entity discussions to reach me just as reliably as item-level mentions, so that I can trust the inbox regardless of where in the item the mention was written
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Tests: assert generated squads/sq-review/sq-feature/sq-task skills + role files carry the convention/guidance, and a no-regression assertion that an @mention in a sub-entity discussion is surfaced by sq inbox; keep pyright + ruff clean.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-06-12T10:00:49Z] Elias Python:
  - Added three tests to test_skills.py: (1) squads skill carries the convention (Scope your comment, all three kind <k> command shapes, inbox rule); (2) sq-review/sq-feature/sq-task per-type skills carry scoped-comment guidance (kind <k> comment shape + comment-scoping convention phrase); (3) role body has comment-scoping pointer to squads skill.
  - Added test_inbox_surfaces_mention_in_subentity_discussion to test_collab.py: no-regression guard for all three sub-entity kinds (story/US1, subtask/ST1, finding/F1) — each @mention in a sub-entity discussion appears in sq inbox.
  - Tests keyed on stable tokens (command shape 'story <k> comment', phrase 'comment-scoping convention') not full sentences. Full suite: 340 passed 1 skipped. pyright: 0 errors. ruff: clean.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T09:56:10Z] Olivia Lead:
  - @python-dev TASK-63 is Ready — content/template only, same shape as TASK-53 (FEAT-40). Goal: ship the comment-scoping convention into the generated skills + role templates.
  - Single source: state the full convention ONCE in squads_skill.md.j2 (the 'Working directly with the operator' / hand-back area). Everywhere else references it. ST1 = squads skill + role template; ST2 = the per-role enter/do/handoff lines in _interactions.py (REVIEW reviewer/dev, FEATURE po/tech-lead, TASK dev) that feed the per-type skills' For-X sections; ST3 = tests + the no-regression inbox assertion.
  - Constraints: no CLI/parsing/inbox code changes; the inbox already picks up sub-entity @mentions; verify a clean 'uv run sq sync' regenerates all skill + role files with markers intact; pyright + ruff clean. Full wording to ship is in the FEAT-62 body — read it.
  - Note: I put the story-scoped rationale in each story's own discussion on FEAT-62 (dogfooding this very convention) — read those panes with 'sq feature 62 show --full --comments' for the per-story reasoning.
<!-- sq:discussion:end -->
