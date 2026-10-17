---
id: FEAT-1092
sequence_id: 1092
type: feature
title: Structural cleanup of engine layering and cohesion
status: Draft
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
  status: Todo
- local_id: US2
  title: Spec threading and loader unification (F6, F8, F15)
  status: Todo
- local_id: US3
  title: Split the oversized files (F9, F10, F12, F7)
  status: Todo
- local_id: US4
  title: Name every sq check finding by a registered rule (F11)
  status: Todo
- local_id: US5
  title: Decide on a DI container (F14)
  status: Todo
- local_id: US6
  title: Apply the comment rule to source and tests (F18, F19)
  status: Todo
created_at: '2026-10-17T03:49:43Z'
updated_at: '2026-10-17T03:50:11Z'
---
<!-- sq:body -->
The structural review of the engine layering and cohesion left thirteen findings open after the 0.16 disposition pass: F3, F5, F6, F7, F8, F9, F10, F11, F12, F14, F15, F18 and F19. The import guard, the role moves and the write-count guard shipped in 0.16. The rest is one coherent piece of structural work, not a set of leftovers to defer one by one, and it lands in 0.17.

**The problem.** The engine works, but its seams are in the wrong places. Role-roster logic sits inside `ServiceCore`, and `_interactions/__init__.py` is an undeclared policy hub. Forty-eight parameters silently fall back to the bundled spec when none is passed, and `Service` is built at eight sites, three of which omit the playbook. Three spec loaders repeat one load shape. Several files have grown past what one reader can hold: `_workflow/_models.py` is 3434 lines and `_maintenance.py` is 3769. `sq check` has eight finding sources and names none of them. The comment rule fails in most source and test files.

The review itself, with the per-finding evidence and sizes, is the reference for every story below.

**Approach.** Each story is one coherent group of findings. Stories are sequenced so that spec threading comes before the splits that touch the same signatures, and the roster extraction informs the DI decision.

**Out of scope**

- Findings already Fixed in 0.16 (F1, F2, F16, F17) and the two closed as WontFix (F4, F13).
- The `-dev` retirement ADR, which takes this review's F1, F2, F3 and F5 as inputs but is its own decision.
- Behaviour changes. Every story is a move, a split or a rule, with no change to what `sq` does for an adopter, except the additive rule key in `sq check --json`.
- Rebuilding the test suite as a whole; the test-comment sweep rides that rebuild.
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
Make the spec and playbook required parameters instead of silently defaulting to the bundled one (48 parameters, 36 production bundled_spec() calls, 22 unused bundled shims). Fold the three hand-written spec loaders into one document descriptor plus one load function. Build Service at one site so no construction omits the playbook, and retire the module-global active-squad-dir and backend registry state. Findings F6, F8 and F15. Size: medium-large (F6), medium (F8), medium (F15); the renderer squad-dir step wants the architect.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Split the oversized files (F9, F10, F12, F7)

<!-- sq:story:US3:body -->
Move the validator registries, load-time validity checks and lifecycle linearisation out of `_workflow/_models.py` (F9, small-medium). Separate `_maintenance.py` into the rebuild corridor and a check mixin of about 1100 lines, with a shared per-file classification primitive (F10, medium-large). Split `_views.py` into its five jobs and fix the two stale insert_view/remove_view names (F12, small). Drop the test-only sub-entity tags, constants and legacy branch (F7, small; the per-kind wrapper port rides the test rebuild).
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
Decide whether to adopt a DI container, as op-pierre ruled on 2026-10-09. The reviewer measured the object graph (six nodes, 0.17 ms construction) and recommends no at today's size, to be reopened if the service is decomposed into collaborators or a long-lived daemon process arrives. The daemon in this milestone is the second condition, so the decision is made with the roster extraction and spec threading in view, and recorded as an architect decision. Finding F14. Size: small, a decision.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — Apply the comment rule to source and tests (F18, F19)

<!-- sq:story:US6:body -->
Bring source and test docstrings and comments under the project comment rule: 95 of 137 source files carry a docstring over five non-blank lines (627 docstrings), and the test files carry 1431 docstrings that fail the check. One per-package sweep with the reviewer per-file tables as the worklist, not one item per file. Source sweep (F18): large. Test sweep (F19): large, riding the deferred test rebuild.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
