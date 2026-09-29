---
id: FEAT-904
sequence_id: 904
type: feature
title: Delete the view projection layer and its declaration grammar
status: Done
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
  status: Done
- local_id: US2
  title: Delete fields/group_by/order_by grammar and its validators
  status: Done
- local_id: US3
  title: Delete ItemSpec.views type-attachment and its orphan-pruning
  status: Done
- local_id: US4
  title: Rebuild milestone_rollup as a one-line source plus a Jinja template
  status: Done
created_at: '2026-09-03T09:10:57Z'
updated_at: '2026-09-24T08:49:39Z'
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
- [2026-09-24T07:50:01Z] Paul Reviewer:
  - REV-960 verdict: **ChangesRequested** (1 high, 1 medium, 6 low).
    
    - F1 (high): the roll-up is not byte-identical to the pre-change render. Before the change, the order inside each partition was status role, then type, then id. The new template drops the status-role level. Reproduced on both the direct and the tag-driven path using a 36f19ab0^ worktree and an interleaved fixture. The ST5 capture-diff test was never written. Either restore the order or get a ruling that the new order is intended.
    - F2 (medium): the retired-key error is the generic unknown-key text, which ST3 asked to replace. In the splat position the message calls the retired key "brand-new".
    - Lows: F3 `render_view` still duplicates `resolve_view_source` (REV-920 F11 is half done). F4 `RELATION_KINDS`/`JsonValue` are dead. F5 false subentity-kind docstring. F6 stale projection/type-attachment prose. F7 narration. F8 CHANGELOG entry missing (overlaps FEAT-908 US3).
    - Verified: the ADR-880 deletion list is gone from src/tests (each grep validated against 36f19ab0^). Retired keys fail loudly in every override shape tried. `--json` for relation kinds matches the tree/list builders. The VS Code client has 0 consumers of the removed shapes. pyright and ruff are clean. Targeted pytest: 1009 passed. REV-920 F9 is resolved; F10 was not re-raised.
    
    @manager please route F1-F8 to @python-dev and route the F1 ordering ruling to @tech-lead.
- [2026-09-24T08:38:36Z] Paul Reviewer:
  - REV-960 re-review verdict: **ChangesRequested** (small). F1-F7 are Verified. F8 is reopened. F9 and F10 are new. No open finding is above low.
    
    - F1 is Verified against the op-pierre ruling. On the 7-member fixture, both paths render type-then-id and match each other. I broke the template in a scratch copy two ways (dropped case_sensitive=True; sorted by status first) and the new test went red each time. The test pins member order by id sequence, not a full byte snapshot. Operator: say if a literal snapshot was meant.
    - F2 is Verified. Every retired-key shape tried, including both splat forms and the key nested under source, is refused as "was retired" with its dotted path. Keys that only look similar (views named fields/group_by, items.bug.fields) still load.
    - Open, all low:
      - F8: the CHANGELOG says source_name is null for playbook, which is false for a playbook view that names a type. The rest of the entry checks out against the code and v0.14.0. Owner: @tech-writer.
      - F9: sq workflow lint rows for retired keys drop the view or type name. The items.views hint says to put the tag in a body, which sq refuses; it should name `view add`. Owner: @python-dev.
      - F10: one test docstring says "a shape the reviewer probed". Owner: @python-dev.
    - Gates: pyright, ruff check and ruff format are clean. Targeted pytest over 129 paths passed 1709. The full suite was not rerun, per the main loop's run.
    
    @manager: three small edits, then this can go to Approved. I'm leaving the Approved transition to you rather than approving my own review.
- [2026-09-24T08:49:39Z] Catherine Manager:
  - Done: TASK-959 delivered, REV-960 Approved, full suite green. Unblocks FEAT-908; TASK-942 (FEAT-948) can now rebase onto it.
<!-- sq:discussion:end -->
