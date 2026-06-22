---
id: TASK-000171
sequence_id: 171
type: task
title: Retrofit existing over-long sub-entity titles into bodies
status: Done
author: tech-lead
refs:
- FEAT-000166
- TASK-000169:depends-on
created_at: '2026-06-23T08:44:30Z'
updated_at: '2026-06-23T10:06:00Z'
---
<!-- sq:body -->
Net-new technical cleanup: retrofit the existing sub-entities whose titles run over the 120-char threshold. A corpus sweep found ~44 such sub-entities (mostly on closed/approved reviews and tasks). The prose is fully recoverable — it currently sits in the titles. This is NOT part of FEAT-000166 (that feature scoped retrofit out), hence no feature parent.

## Sequencing
Depends-on TASK-000169 (the sq check advisory rule). Run this ONLY after that rule lands, so the sq check output is the authoritative worklist — we fix exactly what the check reports rather than eyeballing 44 items by hand. Re-running sq check between fixes confirms the list is shrinking.

## Per-item procedure
For each over-long sub-entity that sq check flags:
1. Move the description text out of the title into the sub-entity body: sq <type> <n> <kind> <k> body -m "…" (e.g. sq review 165 finding F1 body -m "…").
2. Shorten the title to a one-line handle (≤~70 chars, well under the 120 limit) that summarises the item.
3. Preserve the original meaning — the body must carry the full recovered prose; nothing is dropped.
All edits go through sq commands; never hand-edit the .md files or the sq markers.

## Acceptance criteria
- Every sub-entity that the TASK-000169 advisory rule flagged for over-long title is fixed (body set + title shortened).
- sq check reports ZERO over-long-title advisories afterward.
- No structural regressions: sq check otherwise clean, exits 0.
- Closed/approved parent items are not reopened or otherwise mutated beyond the sub-entity title/body retrofit.

## Notes
- Scope is the existing corpus only; new authoring is covered by the FEAT-000166 authoring-time advisory (TASK-000168).
- No subtasks: this is a single mechanical pass driven by the check output; a story/subtask split would not aid implementation or review here.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 171 add-subtask "<title>"`; track with `sq task 171 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-23T08:44:56Z] Olivia Lead:
  - Authored this as net-new technical cleanup, deliberately with NO feature parent: FEAT-000166 explicitly scoped retrofit out, so this can't sit under it. Linked it instead — related→FEAT-000166 for context, depends-on→TASK-000169 so it runs after the sq check advisory rule lands and uses the check output as the exact worklist (no eyeballing 44 items). Procedure is body-then-shorten-title per flagged item; acceptance is sq check reporting zero over-long-title advisories. No subtasks — it's a single mechanical pass, no story mapping (no feature parent). Left in Draft; nothing greenlit to start.
- [2026-06-23T10:02:51Z] Catherine Manager:
  - Retrofit complete via 4 parallel workers (disjoint files by sub-entity type): 34+31 feature stories (product-owner), 25 task subtasks (tech-lead), 17 review findings (reviewer) = 107 — the full sq check worklist.
  - Per item: original title prose rescued into the sub-entity body (verbatim; --append where a real body already existed), title shortened to a ≤70-char handle; --force used for title-only edits on terminal items, no status/severity changed.
  - Acceptance met: sq check reports 0 over-long-title advisories and 0 errors, exit 0. Worst case (REV-097 F5, 781c) verified preserved.
- [2026-06-23T10:06:00Z] Paul Reviewer:
  - REV-000175: Approved. Independent sampling review complete.
  - Objective gate holds: sq check exits 0, --json empty (zero over-long-title advisories, zero errors). Integrity verified: a clean index rebuild from frontmatter shows zero sub-entity title/body diffs vs the live index — frontmatter<->index consistent after all 107 edits.
  - Sampled 12 sub-entities across all three types (incl. REV-097 F5 781c worst case and REV-048 F1-F4): prose recovered verbatim/faithfully into bodies, titles are real handles (<=70c), no info loss. Whole-corpus collateral scan: zero sub-entity status/severity flips, zero parent status changes, zero marker disturbances, pre-existing bodies appended not clobbered. No findings.
<!-- sq:discussion:end -->
