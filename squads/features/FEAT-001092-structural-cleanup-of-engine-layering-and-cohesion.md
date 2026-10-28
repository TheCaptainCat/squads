---
id: FEAT-1092
sequence_id: 1092
type: feature
title: Structural cleanup of engine layering and cohesion
status: Done
author: product-owner
priority: medium
refs:
- MILE-1051:targets
- REV-956
description: 'Home for the 13 open REV-956 findings: roster, spec threading, file
  splits, check registry, DI decision, comment rule.'
subentities:
- local_id: US1
  title: Roster cluster and policy hub extraction (F3, F5)
  status: Done
- local_id: US2
  title: Spec threading and loader unification (F6, F8, F15)
  status: Done
- local_id: US3
  title: Split the oversized files (F9, F10, F12, F7)
  status: Done
- local_id: US4
  title: Name every sq check finding by a registered rule (F11)
  status: Done
- local_id: US5
  title: Decide on a DI container (F14)
  status: Done
- local_id: US6
  title: Apply the comment rule to source and tests (F18, F19)
  status: Done
created_at: '2026-10-17T03:49:43Z'
updated_at: '2026-10-28T12:48:10Z'
---
<!-- sq:body -->
This feature carries thirteen findings of the structural review of the engine
layering and cohesion (REV-956), by the operator's 2026-10-09 ruling: F3, F5,
F6, F7, F8, F9, F10, F11, F12, F14, F15, F18 and F19. Together they are one
coherent piece of structural work.

**The problem.** The engine works, but its seams are in the wrong places.
Role-roster logic sits inside `ServiceCore`, and `_interactions/__init__.py` is
an undeclared policy hub. Dozens of parameters silently fall back to the bundled
spec when none is passed, and `Service` is built at several sites, some of which
omit the playbook. Three spec loaders repeat one load shape. Several files have
grown past what one reader can hold: `_workflow/_models.py` is about 3,500 lines
and `_maintenance.py` about 3,700. `sq check` has eight finding sources and names
none of them. The comment rule fails in most source and test files.

The review, with the per-finding evidence and sizes, is the reference for every
story below. Counts in the stories are the review's; the first act of each story
is to re-measure them.

**Approach.** Each story is one coherent group of findings.

**Out of scope**

- The review's other findings: F1, F2, F16 and F17 (Fixed) and F4 and F13
(WontFix).
- The `-dev` retirement ADR, which takes this review's F1, F2, F3 and F5 as
inputs but is its own decision.
- Behaviour changes. Every story is a move, a split or a rule, with no change to
what `sq` does for an adopter, except the additive rule key in `sq check
--json`.
- Rebuilding the test suite as a whole (FEAT-1096); the test-comment sweep rides
that rebuild.

**Acceptance criteria**

- Each of the thirteen findings is closed on REV-956 as Fixed with the commit, or
as WontFix with a recorded reason (F14 is a decision).
- The full suite, pyright, ruff and `sq check` are clean after every story, with
no test assertion changed to fit a move.
- `sq check --json` output is unchanged except for the additive rule key (US4);
generated files (CLAUDE.md, pointers, skills) are byte-identical before and after
the structural stories, on a pinned roster.
- The layering guard (the import-edge table) is updated in the same change as
any new edge, and passes.
- No module-level mutable state is added; the active-squad-dir and backend
registry state named in US2 is threaded or removed.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1092 add-story "As a <role>, I want … so that …"`; track with `sq feature 1092 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Roster cluster and policy hub extraction (F3, F5)

<!-- sq:story:US1:body -->
Extract the roster projection (about 400 lines, 19 methods in ServiceCore, used by six mixins) into its own collaborator, and move the roughly 810 lines of policy in `_interactions/__init__.py` (skill naming, view-name constants, roster liveness, orphan guides, cheatsheet anchoring) into declared modules so the init stops loading the bundled playbook at import. Findings F3 and F5. Size: medium each, mechanical moves with no behaviour change.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Spec threading and loader unification (F6, F8, F15)

<!-- sq:story:US2:body -->
Make the spec and playbook required parameters instead of silently defaulting to the bundled one (48 parameters and about 39 production bundled_spec() calls plus unused bundled shims). Fold the three hand-written spec loaders into one document descriptor plus one load function. Build Service at one site so no construction omits the playbook, and retire the module-global active-squad-dir and backend registry state. Findings F6, F8 and F15. Size: medium-large (F6), medium (F8), medium (F15); the renderer squad-dir step wants the architect. Acceptance: no production call falls back to the bundled spec silently, Service has one construction site, and the suite passes unchanged.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Split the oversized files (F9, F10, F12, F7)

<!-- sq:story:US3:body -->
Move the validator registries, load-time validity checks and lifecycle linearisation out of `_workflow/_models.py` (F9, small-medium). Separate `_maintenance.py` into the rebuild corridor and a check mixin of about 1100 lines, with a shared per-file classification primitive (F10, medium-large). Split `_views.py` into its five jobs and fix the two stale insert_view/remove_view names (F12, small). Drop the test-only sub-entity tags, constants, legacy branch and per-kind service wrappers (F7, small).
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Name every sq check finding by a registered rule (F11)

<!-- sq:story:US4:body -->
Give each of the eight `sq check` finding sources a rule name, carried as an additive key in `--json`, with a registry saying which rules are binding, a guard keeping the registry complete, and a docs paragraph listing them for adopters. Finding F11. Size: medium.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Decide on a DI container (F14)

<!-- sq:story:US5:body -->
Decide whether to adopt a DI container, as op-pierre ruled on 2026-10-09. The object graph measures six nodes and 0.17 ms construction; at that size the review recommends against one, to be reopened if the service is decomposed into collaborators or a long-lived daemon process arrives. The milestone's daemon is the second condition, so the decision weighs the roster extraction and spec threading, and is recorded as an architect decision. Finding F14. Size: small, a decision.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — Apply the comment rule to source and tests (F18, F19)

<!-- sq:story:US6:body -->
Bring source and test docstrings and comments under the project comment rule: 95 of 137 source files carry a docstring over five non-blank lines (627 docstrings), and the test files carry 1431 docstrings that fail the check. One per-package sweep with the review's per-file tables as the worklist, not one item per file. The source sweep (F18) is large. The test sweep (F19) is large and rides the test-suite rebuild (FEAT-1096). Acceptance: the mechanical check passes on every swept file, and no behaviour changes.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T19:43:22Z] `product-owner` Nina Product:
  - @tech-lead needs a breakdown into tasks (no tasks yet). Premises re-measured 2026-10-24: file sizes and bundled_spec call count still close to the review; counts in stories are to be re-measured at the start of each. Acceptance criteria added.
- [2026-10-24T21:56:18Z] `tech-lead` Olivia Lead:
  - Broken down into four tasks:
    - TASK-1124: behaviour-free moves for US1-US3 (F3, F5-F10, F12), eight subtasks. Ready.
    - TASK-1125: the composition root (F15). Draft, waiting on the DI decision (US5, F14), with my recommendation to @op-pierre on the task.
    - TASK-1126: check rule names (US4, F11). Ready.
    - TASK-1127: the source comment sweep (US6, F18). Ready.
    US5 is a decision, not a task: @architect records it as an ADR once op-pierre rules.
    F19 rides the rebuild as a new subtask on TASK-1112 (the new root is held to the one-line test docstring rule). The remainder of F7, deleting the per-kind service wrappers, is a new subtask on TASK-1116, once the old suite is gone.
    Order: TASK-1123 (FEAT-916), then TASK-1124, TASK-1125, TASK-1126, run serially by one developer since they share `_services/_base.py`, `_cli/_common.py` and `_cli/_main.py`. Then the test rebuild (TASK-1111 depends on all four). Why: the rebuild's ledger names seams by module and function, its mutation patches target `src/`, and its biggest tables (the check-by-type table, the `-C` gate differential) run through exactly the code these tasks move. Moving the code after the ledger is written would make the rebuild port everything twice. TASK-1127 changes prose only, moves no seam, and runs beside the rebuild.
    TASK-1124 also depends on TASK-1106 (new `_interactions` token resolver) and TASK-1077 (validator wording in the same files). TASK-1126 depends on TASK-1104, whose new check warnings it names.
- [2026-10-24T21:59:26Z] `architect` Robert Architect:
  - US5 (REV-956 F14) is ADR-1128, Proposed with options A/B and a recommendation for A; awaiting @op-pierre.
- [2026-10-28T12:20:41Z] `op-pierre` Pierre Chat:
  - 2026-10-28: the F7 remainder (the per-kind sub-entity wrappers left in _services/_subentities.py) gets a small task under this feature, in 0.17: delete the wrappers, move the two test helpers to the generic API, drop the exemptions.
- [2026-10-28T12:48:09Z] `manager` Catherine Manager:
  - Closed: TASK-1124..1127 and TASK-1215 Done with Approved reviews; REV-956 settled (F7 via TASK-1215, F14 WontFix per ADR-1128); narration sweep and CHANGELOG done.
<!-- sq:discussion:end -->
