---
id: TASK-307
sequence_id: 307
type: task
title: Sweep dogfood tree of existing status/lifecycle body banners
status: Done
parent: FEAT-264
author: tech-lead
assignee: python-dev
refs:
- TASK-306:depends-on
subentities:
- local_id: ST1
  title: Enumerate + clean flagged item bodies via the guard
  status: Done
  assignee: python-dev
  story: US1
- local_id: ST2
  title: Verify markers/frontmatter intact after the sweep
  status: Done
  story: US1
created_at: '2026-07-06T12:13:33Z'
updated_at: '2026-07-06T12:50:03Z'
---
<!-- sq:body -->
**Corpus cleanup — the bounded dogfood sweep.** With the guard from TASK-306 in place, run `sq check` across the live `squads/` tree and resolve every warn the new banner rule emits. Let the detector — not eyeballing — define the worklist; that is why this task **depends on TASK-306**.

For each flagged body/`description:`: remove the leading status/lifecycle banner. Where the information is worth keeping, **relocate it to a dated discussion comment** (state-at-a-point-in-time is history and belongs in the append-only record), not back into the body. All edits go through `sq … body -m` / `sq … comment` — never hand-edit the `.md`; sq: markers and frontmatter stay intact.

**Known offenders to address at minimum:** the ADR that once opened with a `STATUS: Proposed` banner but is now Accepted (the drift the feature cites); and any TASK/ADR/review carrying a leading `BLOCKED ON …` or hand-written `## Status` self-declaration surfaced by the run.

**Done when:** the new rule reports **zero** warnings across the `squads/` tree; every edited item still parses (valid YAML frontmatter, intact markers) with its frontmatter `status:` unchanged.

**Scope call (recorded here):** cleaning existing violations is **IN-SCOPE** per acceptance criterion 5, delivered as this bounded sweep scheduled **after** the guard lands. Keeping it a separate task keeps TASK-306's code + test-fixture reconciliation distinct from live-tree data cleanup. The CLAUDE.md `## Status` decision is NOT here — it rides in TASK-305 (the sq check rule never scans CLAUDE.md).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 307 add-subtask "<title>"`; track with `sq task 307 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done | python-dev | Enumerate + clean flagged item bodies via the guard | US1 |
| ST2 | Done |  | Verify markers/frontmatter intact after the sweep | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Enumerate + clean flagged item bodies via the guard

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US1 — The tracker's status is never contradicted by body prose
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Run `sq check` over the live squads/ tree and collect every warn from the new banner rule. For each flagged item, remove the leading banner from the body/description and, where the state is worth keeping, move it to a dated discussion comment via `sq … comment` (never back into the body). Edit only through `sq … body -m` — never hand-edit the .md. Re-run until the rule reports zero warnings. Done when the sweep is complete and the guard is silent across squads/.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Verify markers/frontmatter intact after the sweep

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US1 — The tracker's status is never contradicted by body prose
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
After the sweep, confirm every edited item still parses: valid YAML frontmatter, intact sq: markers, and frontmatter `status:` unchanged (only body/description prose moved). Spot-check the known offenders (the once-`STATUS: Proposed` ADR, any `BLOCKED ON …`/`## Status` self-declarations). Done when all touched items are structurally intact and the board's status fields are untouched.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
