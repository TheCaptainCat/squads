---
id: FEAT-904
sequence_id: 904
type: feature
title: Delete the view projection layer and its declaration grammar
status: Draft
parent: EPIC-897
author: product-owner
priority: urgent
refs:
- MILE-867:targets
- ADR-880:implements
- FEAT-905:depends-on
- FEAT-907:depends-on
description: Remove the flattened-record middle layer, fields/group_by/order_by, and
  type-attachment; rebuild milestone_rollup as source + Jinja template
subentities:
- local_id: US1
  title: Delete the projection middle layer (Cell/ViewRecord/Projection/project et
    al.)
  status: Todo
- local_id: US2
  title: Delete fields/group_by/order_by grammar and its validators
  status: Todo
- local_id: US3
  title: Delete ItemSpec.views type-attachment and its orphan-pruning
  status: Todo
- local_id: US4
  title: Rebuild milestone_rollup as a one-line source plus a Jinja template
  status: Todo
created_at: '2026-09-03T09:10:57Z'
updated_at: '2026-09-04T08:08:13Z'
---
<!-- sq:body -->
## Why

The projection middle layer reimplements the template language, worse, and forces heterogeneous
records into a lossy flattened shape. Nothing consumes its machine-readable half. It deletes.

## Scope

- Delete: `_RawRecord`, `Cell`, `ViewFieldMeta`, `ViewRecord`, `ViewGroup`, `Projection`,
  `project`, `_cell`, `_badge_cell`, `_sort_key`, `_BASE_RESOLVERS`, `projection_json`.
- Delete the declaration grammar: `ViewSpec.fields`, `group_by`, `order_by`.
- Delete the validators that existed only to prove that grammar resolved:
  `_check_view_fields`, `_check_item_views`, `VIEW_BASE_FIELDS_BY_SOURCE`. `_check_view_source`
  survives — a source's `name` resolving against its `kind`'s vocabulary is real and cheap.
- Delete type-attachment: `ItemSpec.views` and `_prune_orphaned_type_owned_views` with it.
- Loading a spec that still declares any of the four removed keys (`fields`, `group_by`,
  `order_by`, `items.<type>.views`) is a **load-time error naming the key**, not a silent drop
  — this is also the adopter-facing signal FEAT-908 documents the upgrade against.
- `[views.milestone_rollup]` reduces to its one-line `source`; `templates/views/
  milestone_rollup.md.j2` is rewritten with Jinja `groupby`/`sort` to reproduce today's
  grouping-by-status-role and ordering-by-type-then-id.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 904 add-story "As a <role>, I want … so that …"`; track with `sq feature 904 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Delete the projection middle layer (Cell/ViewRecord/Projection/project et al.)

<!-- sq:story:US1:body -->
As a maintainer, I want the projection middle layer deleted (_RawRecord, Cell, ViewFieldMeta, ViewRecord, ViewGroup, Projection, project, _cell, _badge_cell, _sort_key, _BASE_RESOLVERS, projection_json), so a view's data isn't force-flattened into synthetic cells before it reaches a template.

Acceptance: none of the listed constructs are reachable from sq workflow view, sq check, or rendering; a grep for each name returns nothing outside history/changelog.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Delete fields/group_by/order_by grammar and its validators

<!-- sq:story:US2:body -->
As a maintainer, I want fields/group_by/order_by and the validators that existed only to prove they resolved deleted, so no dead validation surface survives the grammar it checked.

Acceptance: [views.<name>] accepts only source; _check_view_fields, _check_item_views, and VIEW_BASE_FIELDS_BY_SOURCE are gone; _check_view_source survives, still validating a source's name against its kind's vocabulary; loading a spec that still declares fields/group_by/order_by is a load-time error naming the removed key, not a silent drop.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Delete ItemSpec.views type-attachment and its orphan-pruning

<!-- sq:story:US3:body -->
As a maintainer, I want ItemSpec.views and _prune_orphaned_type_owned_views deleted along with the grammar they served, so type-attachment doesn't survive as an unused seam.

Acceptance: items.<type>.views is gone from the spec model; loading a spec that still declares it is a load-time error naming the key; _prune_orphaned_type_owned_views is deleted, not merely unreachable.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Rebuild milestone_rollup as a one-line source plus a Jinja template

<!-- sq:story:US4:body -->
As the owner of the bundled milestone roll-up, I want [views.milestone_rollup] reduced to source = { kind = ref, name = targets } and templates/views/milestone_rollup.md.j2 rewritten with Jinja groupby/sort to reproduce today's grouping-by-status-role, ordering-by-type-then-id output, so the roll-up keeps working with the deleted grammar gone.

Acceptance: rendered roll-up output for a fixed fixture milestone (same members, same statuses) is unchanged from pre-change output; sq workflow view milestone_rollup <id> and the tag-driven render (FEAT-905/907) both produce it.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-04T08:08:13Z] Olivia Lead:
  - REV-920 F10: self --json spec identity ({schema_version, override}) reports override-file-existence, not merge outcome, and cannot distinguish two different override documents. Not fixed under TASK-921 (not load-bearing for any client today, and this feature is already the natural place to reconsider self/playbook JSON shape). Worth a look when this feature touches self/playbook --json.
  - F9 (inert fields/group_by/order_by on a non-relation view) and part of F11 (ViewsMixin repeating the resolve-a-view preamble, one copy being resolve_view itself) are resolved for free by this features own scope -- noted here so the resolution is deliberate, not accidental.
<!-- sq:discussion:end -->
