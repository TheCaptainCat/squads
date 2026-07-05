---
id: FEAT-62
sequence_id: 62
type: feature
title: 'Comment-scoping convention: sub-entity discussions vs main discussion'
status: Done
parent: EPIC-12
author: product-owner
priority: medium
refs:
- FEAT-26
subentities:
- local_id: US1
  title: Skills tell agents which comment command to use for each scope
  status: Done
- local_id: US2
  title: Sub-entity panes hold their scoped discussion, not a cross-cutting blob
  status: Done
- local_id: US3
  title: Sub-entity @mentions reach the inbox as reliably as item-level ones
  status: Done
created_at: '2026-06-12T09:49:28Z'
updated_at: '2026-06-23T10:00:43Z'
---
<!-- sq:body -->
## Problem

Sub-entity discussions exist in squads — every story, subtask, and finding has its own `:discussion` region, writable via `sq <type> <n> <kind> <k> comment` — but no generated guidance ever teaches agents to use them. Every skill teaches only the item-level command (`sq <type> <n> comment`), so agents follow the docs and ignore the sub-entity path entirely.

The consequence is information pollution. When a reviewer closes findings with fix rationale or a developer resolves an acceptance question, those notes go into the item's main discussion as a single undifferentiated blob. The next reader of a specific finding or story must hunt through the parent item's full discussion to find what is relevant to that unit of work.

**Live specimen (2026-06-12):** REV-61 has three findings — F1, F2, F3 — each with its own discussion region. The fix explanations for all three went into the review's main discussion as one block, because the sq-review skill and the squads skill taught no other convention. Any agent reading the dossier with `--full --comments` sees the sub-entity pane for F1 empty, with the rationale buried elsewhere.

**Root cause:** the capability gap is on the write side. FEAT-26 closed the read side — the rendered `--full --comments` dossier now shows each sub-entity's own discussion in its pane. But no skill was updated to teach when and how to write into those panes.

## Value

When agents write comments to the right scope, the dossier reads as a self-contained brief: the reviewer opening a finding pane sees exactly the acceptance debate and fix rationale for that finding, not a cross-cutting blob. Parallel threads stay separated without manual filtering.

This is also reliability of inference. Today, an agent reading a dossier cannot distinguish 'this finding has no discussion' from 'the discussion exists but is in the wrong place'. Scoped comments make silence meaningful again.

## Scope

**Convention (content-only — no CLI changes):**

_Sub-entity discussion_ — anything whose meaning is scoped to that specific story, subtask, or finding:
- Finding: fix rationale, reproduction details, verification notes, 'agreed — closing this one'
- Story: acceptance clarification, story-specific blocker or question, scope refinement between product owner and implementer
- Subtask: implementation note, decision local to this unit of work, sub-assignee check-in

_Main item discussion_ — cross-cutting material:
- Handoff comments and @mentions (all @mentions, regardless of what triggered them — see below)
- Decisions affecting more than one sub-entity or the item as a whole
- Status summaries for the item level ('all findings resolved, ready for re-review')
- Anything that must reach the item's assigned reviewer, owner, or the next agent in the loop

**The inbox rule:** `sq inbox` reads the entire item file, so @mentions placed in a sub-entity discussion _are_ visible in the inbox (empirically verified 2026-06-12: created a task with a subtask, wrote a sub-entity comment containing `@qa`, ran `sq inbox qa`, and the mention appeared). There is no inbox gap to work around. The guidance can safely say: @mentions go in whichever discussion region is appropriate to their scope — and the inbox will pick them up either way. However, the handoff sentence ('hand back with a comment') naturally reads as item-level, and keeping @mentions that signal task-level handoffs in the main discussion makes the item's conversation easier to skim. Recommendation: prefer main discussion for @mentions that announce a transition or request action from the next agent; sub-entity discussion for @mentions that are scoped questions (e.g. 'F2 — @reviewer does this fix satisfy the requirement?').

**Surfaces to update (content, regenerated via `sq sync`):**
1. **`squads` skill** — 'Hand back through `sq`' section: add a sentence distinguishing sub-entity comment from item comment, with the convention above
2. **`sq-review` skill** — the reviewer's and developer's For-X sections: explicit guidance on writing finding-scoped comments when closing or responding to a finding
3. **`sq-feature` skill** — product-owner and tech-lead For-X sections: guidance on writing story-scoped comments for acceptance clarification
4. **`sq-task` skill** — developer For-X section: subtask-scoped comments for implementation notes
5. **Role templates (working agreements)** — a brief statement of the convention so it is visible when an agent loads its role
6. Out of scope: changes to the `sq` CLI, sub-entity comment parsing, or inbox implementation. No code changes.

## Acceptance

- An agent following the updated squads skill can answer 'where does this comment go?' without ambiguity for all three sub-entity types.
- The REV-61 scenario replayed under the new guidance: finding F1's fix rationale lands in `sq review N finding 1 comment`, not the review's main discussion. A reader running `sq review N show --full --comments` sees the rationale in F1's pane.
- Story-level acceptance questions in a feature are recorded via `sq feature N story K comment`, visible in the story's pane.
- The inbox continues to surface all @mentions correctly after the guidance change (no regression introduced by convention).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 62 add-story "As a <role>, I want … so that …"`; track with `sq feature 62 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | Skills tell agents which comment command to use for each scope |
| US2 | Done |  | Sub-entity panes hold their scoped discussion, not a cross-cutting blob |
| US3 | Done |  | Sub-entity @mentions reach the inbox as reliably as item-level ones |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Skills tell agents which comment command to use for each scope

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As an agent writing a comment, I want the skills I load to tell me whether to use `sq <type> <n> <kind> <k> comment` or `sq <type> <n> comment`, so that I never route fix rationale or acceptance notes to the wrong discussion.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
- [2026-06-12T09:55:58Z] Olivia Lead:
  - Single-source decision for the write-side guidance: the full convention wording lives ONLY in the squads skill (squads_skill.md.j2). The per-type skills (via _interactions.py role lines) and the role template carry a short pointer + at most one example — mirroring how TASK-53 kept the dual-regime principle in one place. This satisfies US1's 'the squads skill explicitly names the sub-entity command and gives a concrete example' while keeping the per-role skill text drift-free.
  - Covered in TASK-63 ST1.
- [2026-06-12T10:03:12Z] Paul Reviewer:
  - US1 verified. The squads skill (squads.md) names sq <type> <n> <kind> <k> comment as the sub-entity command and gives one concrete example per kind via the scope table (finding/story/subtask), plus the inbox @mention rule. Single-source discipline holds: per-type skills and role template carry pointers + at most one example, all referencing the comment-scoping convention by name — no restatement that can drift. test_squads_skill_teaches_comment_scoping_convention and test_per_type_skills_carry_scoped_comment_guidance assert the canonical text once and the pointers everywhere else, keyed on stable command-shape tokens.
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Sub-entity panes hold their scoped discussion, not a cross-cutting blob

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As an agent reading a dossier with `--full --comments`, I want each sub-entity pane to contain the discussion that is scoped to it, so that I can brief on a finding or story without hunting through the parent item's main discussion.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
- [2026-06-12T09:55:59Z] Olivia Lead:
  - US2 (panes read self-contained) is the runtime payoff of the write-side guidance — no separate template work. The _interactions.py edits in ST2 (REVIEW reviewer/dev, FEATURE po/tech-lead, TASK dev) are what cause agents to write into the right pane so the dossier renders as intended. The REV-61 replay is the acceptance check, exercised under ST3's tests.
  - Covered in TASK-63 ST2.
- [2026-06-12T10:03:15Z] Paul Reviewer:
  - US2 verified by mental replay of the REV-61 specimen. An agent reading the regenerated sq-review skill's reviewer/dev Do lines is told to run sq review <n> finding <k> comment for fix rationale/verification, landing it in the finding's own pane; the main discussion is reserved for cross-cutting verdict and handoff mentions. Same for story panes via sq-feature po/tech-lead lines. The _interactions.py edits are the runtime cause; the dossier renders self-contained as intended.
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Sub-entity @mentions reach the inbox as reliably as item-level ones

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As an agent reading my inbox, I want @mentions placed in sub-entity discussions to reach me just as reliably as item-level mentions, so that I can trust the inbox regardless of where in the item the mention was written.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
- [2026-06-12T09:55:59Z] Olivia Lead:
  - US3 is a no-regression guard: the inbox already surfaces sub-entity @mentions (PO verified 2026-06-12). ST3 adds/keeps a test asserting an @mention written in a sub-entity discussion is returned by sq inbox <role>, and confirms the new guidance only adds precision — it never pushes correctly-scoped @mentions out of sub-entity discussions.
  - Covered in TASK-63 ST3.
- [2026-06-12T10:03:18Z] Paul Reviewer:
  - US3 verified. test_inbox_surfaces_mention_in_subentity_discussion (test_collab.py) is a real no-regression guard covering all three sub-entity kinds — a mention in a story, subtask, and finding discussion each surfaces via sq inbox. Suite green (340-ish passed, 1 skipped). The new guidance only adds precision; it never pushes correctly-scoped @mentions out of sub-entity discussions — the skill text explicitly says the inbox never misses a mention and that scoped @mentions are fine.
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T09:50:46Z] Pierre Chat:
  - No agent uses the subitem comments — only the main part. REV-61 has findings F1, F2, F3 with their own discussion but all the fix explanations went into the review's main discussion as one blob. The capability exists, nobody taught it.
- [2026-06-12T09:50:54Z] Nina Product:
  - Spec authored 2026-06-12. Empirical inbox check confirmed: @mentions in sub-entity discussions are picked up by `sq inbox` (the inbox reads the entire file). No inbox gap — the convention can permit sub-entity @mentions for scoped questions without reliability risk. Parent chosen as EPIC-12 (Road to 1.0) rather than EPIC-38 (CLI frontend) because this is a content-only/onboarding feature in the same vein as FEAT-40 and FEAT-41, not a CLI change. Ref to FEAT-26 as `related` — they are the read/write pair of the dossier model: FEAT-26 made sub-entity panes visible in the dossier; this feature teaches agents to write into them. Implementation is `sq sync`-driven content changes to skills and role templates — no CLI code.
- [2026-06-12T09:56:10Z] Olivia Lead:
  - Broken down into TASK-63 (assigned @python-dev, Ready). Single task, content-only, mirrors TASK-53's shape. Story-scoped notes are in each story's discussion; feature moved to InProgress.
- [2026-06-12T10:01:08Z] Elias Python:
  - TASK-63 complete. Comment-scoping convention shipped across all three surfaces: (1) squads_skill.md.j2 — canonical convention block with table covering finding/story/subtask examples plus the inbox @mention rule (single source, nothing duplicated elsewhere); (2) _interactions.py — terse pointers in REVIEW reviewer + dev, FEATURE product-owner + tech-lead, TASK dev, each referencing the squads skill by name; (3) role.md.j2 — one-sentence working-agreement pointer. sq sync regenerated all role and skill files; sq check clean; 340 tests passed, pyright 0 errors, ruff clean.
  - Subtask-scoped implementation notes are in each of ST1/ST2/ST3's own discussions. @reviewer ready for review.
- [2026-06-12T10:03:25Z] Paul Reviewer:
  - APPROVED — TASK-63 review (Paul Reviewer). All acceptance criteria met; single-source discipline confirmed (full convention lives only in squads.md; per-type skills + role template carry pointers + at most one example, no restatable text that can drift). Content matches the spec: preference not hard rule, inbox surfaces mentions everywhere, scoped vs cross-cutting split accurate. The For-<role> additions in _interactions.py read tersely — one bullet per line, each pointing at the convention by name (no line bloat). Per-story verification notes are on US1/US2/US3 discussions.
  - Gates all green: pytest passed (1 skipped), pyright 0 errors, ruff check + format clean, sq check clean. sq sync is idempotent — verified two consecutive runs produce byte-identical diffs, no drift; CLAUDE.md correctly untouched (convention is in skill/role bodies). No review item opened — no changes required.
<!-- sq:discussion:end -->
