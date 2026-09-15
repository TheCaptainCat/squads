---
id: FEAT-902
sequence_id: 902
type: feature
title: 'Squad-global validators: parent outcomes, cycles, WIP, staleness'
status: Draft
parent: EPIC-540
author: product-owner
priority: low
refs:
- ADR-864:implements
- FEAT-898:depends-on
- MILE-934:targets
description: Five squad-wide opt-in checks from ADR-864 Part 2, none bundled by default
subentities:
- local_id: US1
  title: 'children_settled_with_parent: flag a settled parent with open children'
  status: Todo
- local_id: US2
  title: 'dependency_acyclic: flag a cycle among dependency edges'
  status: Todo
- local_id: US3
  title: 'wip_limit: flag an assignee over a declared active-item cap'
  status: Todo
- local_id: US4
  title: 'unassigned_active: roll up unassigned active items into one line'
  status: Todo
- local_id: US5
  title: 'stale_active: flag an active item untouched for n days, via the injectable
    clock'
  status: Todo
created_at: '2026-09-03T09:02:36Z'
updated_at: '2026-09-09T14:46:16Z'
---
<!-- sq:body -->
## Why

Five squad-wide checks named in ADR-864 Part 2, each opt-in, none bundled by default. One of
them names a failure this team has already hit more than once.

## Scope (all warn, catalog-only, squad-global; depends on FEAT-898)

- `children_settled_with_parent` -- a parent at a settled status with open children. **For
  everyone, and specifically for the failure this team has hit repeatedly**: a parent closed
  against its outcomes-not-yet-delivered rather than against its children (see memory note
  "Close epics against outcomes, not children" -- EPIC-538 went Done with three unbuilt
  features and the design got re-derived weeks later; this feature was itself decided by the
  same principle, this session, for EPIC-540/EPIC-897).
- `dependency_acyclic` -- a cycle among dependency-semantic edges, which `sq blocked` would
  otherwise render as a permanent mutual block.
- `wip_limit:<n>` -- more than *n* items at an active-role status for one assignee. Explicitly
  not for this squad (we run one agent per role, not kanban WIP discipline) -- named as the
  clearest example of the tier: a real check, nobody's defect, wrong to bundle.
- `unassigned_active:<n>` -- the roll-up of the per-item `assignee_present` check (FEAT-901),
  for a board owner who wants one line instead of fifty.
- `stale_active:<days>` -- an item at an active status untouched for *n* days. **Admitted with
  one binding condition**: it reaches the clock only through the injectable clock the rest of
  the codebase already uses (`clock.now()`), and it is **never bundled** by default for any
  squad -- so `sq check` stays deterministic between two runs over an unchanged corpus unless a
  squad has knowingly selected it.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 902 add-story "As a <role>, I want … so that …"`; track with `sq feature 902 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — children_settled_with_parent: flag a settled parent with open children

<!-- sq:story:US1:body -->
As a team that has closed a parent against its children rather than its outcomes before, I want a settled parent (epic/feature/task) with open children flagged, so an unbuilt outcome can't vanish silently the way EPIC-538 did with three unbuilt features.

Acceptance: warn, catalog-only, squad-global; fires when a parent reaches a settled status while any child remains open; this project selects it in its own spec.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — dependency_acyclic: flag a cycle among dependency edges

<!-- sq:story:US2:body -->
As a team using dependency edges, I want a cycle among blocks/depends-on edges flagged, since sq blocked would otherwise render it as a permanent mutual block with no way out.

Acceptance: warn, catalog-only, squad-global; detects a cycle restricted to dependency-semantic edges (not every ref kind).
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — wip_limit: flag an assignee over a declared active-item cap

<!-- sq:story:US3:body -->
As a team running a kanban discipline, I want to declare a WIP cap per assignee and be warned when it's exceeded.

Acceptance: warn, catalog-only, squad-global, declared parameter wip_limit:<n>; explicitly not selected in this project's own spec -- named as the clearest example of a real check that is nobody's defect and would be wrong to bundle.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — unassigned_active: roll up unassigned active items into one line

<!-- sq:story:US4:body -->
As a board owner, I want one roll-up line for how many active items are unassigned, instead of reading fifty individual assignee_present warnings.

Acceptance: warn, catalog-only, squad-global, declared parameter unassigned_active:<n>; the roll-up of FEAT-901's per-item assignee_present check.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — stale_active: flag an active item untouched for n days, via the injectable clock

<!-- sq:story:US5:body -->
As a team running a long-lived board, I want an active item untouched for n days flagged.

Acceptance: warn, catalog-only, squad-global, declared parameter stale_active:<days>; reads the time through the codebase's existing injectable clock (clock.now()), never datetime.now() directly; never bundled by default for any squad, so sq check stays deterministic between two runs over an unchanged corpus unless a squad has knowingly selected it; this project does not select it by default.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
