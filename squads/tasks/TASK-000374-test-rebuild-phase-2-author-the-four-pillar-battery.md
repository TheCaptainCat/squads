---
id: TASK-374
sequence_id: 374
type: task
title: 'Test rebuild Phase 2: author the four-pillar battery'
status: Draft
parent: FEAT-231
author: tech-lead
subentities:
- local_id: ST1
  title: Behavior-named taxonomy across the four pillars, no dev-archaeology
  status: Todo
  story: US1
- local_id: ST2
  title: 'Fast by default: mark scale slow, flip addopts to -m not slow, under 30s'
  status: Todo
  story: US2
- local_id: ST3
  title: Each invariant asserted once at the lowest meaningful layer
  status: Todo
  story: US3
created_at: '2026-07-10T04:48:20Z'
updated_at: '2026-07-10T04:50:03Z'
---
<!-- sq:body -->
## Phase 2 — Author the four-pillar battery

Third phase of the FEAT-231 rebuild, and the bulk of the authoring. Write the new suite against the
**shipped, final** generic spec engine (EPIC-280 + EPIC-335 landed — no ItemType/Status enums,
byte-identical-default behaviour). **The old flat suite stays in place and green throughout; this
phase only adds.** Structure the battery around the four pillars from the manager's strategy comment,
not per-type re-testing:

### The four pillars (parallelizable work-streams — mostly separate subdirs)
1. **Generic-engine-once** (`tests/unit/`, some `tests/service/`) — test the mechanism a single
   time, keyed on a spec: transitions / terminal / parent-allowed / capability flags / badge
   collections derived from a spec, NOT re-tested per built-in type. This is where the suite shrinks.
2. **Spec-as-artifact + goldens** (`tests/unit/` + `tests/goldens/`) — the bundled spec is now a
   tested artifact: assert its shape and correct flag/badge values; disciplined goldens for
   generated artifacts (CLAUDE.md/AGENTS.md sections, skill pointer bodies, rendered templates) with
   all inputs pinned (roster, flags, frozen clock) and one golden per distinct rendering path.
3. **Behavioural spine** (`tests/cli/`, `tests/integration/`) — a SMALL end-to-end set proving the
   configured types behave: `sq check`, retype, skill generation, create/transition/comment happy
   paths. Absorb the thin acceptance tests EPIC-280/335 already added (e.g. custom-type, custom
   badge-axis, load-boundary-vocab, spine-characterization) as characterization seeds — migrate,
   rename to behavior-named form, dedup against pillar 1.
4. **Failure / edge surface (first-class — the part the old enum suite structurally lacked)** —
   budget for this explicitly: invalid/unknown vocab at the load boundary (the FEAT-208 F1 miss:
   corrupt frontmatter silently indexed then crashes `sq check`), malformed spec, reserved-vocab
   violations (only role/skill/operator reserved; the 7 work types fully overridable), override-merge
   conflicts, custom-type / custom-status scenarios.

### Cross-cutting requirements (realize the user stories)
- **US1 — behavior-named:** every file/class/function name completes "This system guarantees
  that…". No `layer_a/b`, `golden_lock`, `FEAT-`/`TASK-`/`ADR-` refs, no ticket-ID filenames.
- **US3 — each invariant once, at the lowest meaningful layer:** use the Phase-0 duplicate-invariant
  clusters to collapse redundant multi-layer assertions. CLI tests prove clean exit + parseable
  output, not model-field well-formedness (that's a unit test).
- **US2 — fast by default:** mark scale/stress tests `@pytest.mark.slow` and flip
  `pyproject.toml` `addopts` to include `-m 'not slow'` (keep `-n auto`). The deferred wall-clock
  win folds in HERE. Target: default run < 30s; `uv run pytest -m slow` runs the scale paths.
- Determinism per Principle 7: `frozen_time`, tmp_path isolation, env stripped, order-independent.

### Dependencies
Depends on Phase 1 (scaffolding + conftest). Blocks Phase 3. The four pillars are internally
parallelizable (mostly distinct subdirs), but if authored by concurrent agents they share
`conftest.py`/`CONVENTIONS.md`/`tests/goldens/` — sequence or worktree-isolate those touch points to
avoid collisions. Do NOT delete any old test here.

### Acceptance
- All four pillars authored; every Phase-0 ledger row has a corresponding new-suite test.
- Default `uv run pytest` (with `-m 'not slow'`) green and under 30s; `-m slow` green.
- Zero dev-archaeology names in the new tree; `uv run sq check` clean; old suite still green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 374 add-subtask "<title>"`; track with `sq task 374 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Behavior-named taxonomy across the four pillars, no dev-archaeology | US1 |
| ST2 | Todo |  | Fast by default: mark scale slow, flip addopts to -m not slow, under 30s | US2 |
| ST3 | Todo |  | Each invariant asserted once at the lowest meaningful layer | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Behavior-named taxonomy across the four pillars, no dev-archaeology

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — Behavior-named tests, not development archaeology
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Fast by default: mark scale slow, flip addopts to -m not slow, under 30s

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US2 — Default test run under 30 seconds
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Each invariant asserted once at the lowest meaningful layer

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
**Implements:** US3 — Each invariant asserted once, at the right layer
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
