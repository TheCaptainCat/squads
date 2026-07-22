---
id: FEAT-568
sequence_id: 568
type: feature
title: 'Validator catalog: seed checks + category/type assignment'
status: Draft
parent: EPIC-540
author: product-owner
priority: medium
refs:
- FEAT-567
- ADR-541
subentities:
- local_id: US1
  title: lift seed catalog verbatim from today's _check_* methods
  status: Todo
- local_id: US2
  title: category bundles + per-type validators + the two new enforcements
  status: Todo
created_at: '2026-07-22T08:38:35Z'
updated_at: '2026-07-22T08:39:09Z'
---
<!-- sq:body -->
## Capability

Populate the closed validator catalog with today's `_check_*` methods lifted
verbatim (per ADR-541's seed list), and build the declarative `.overrides`
**assignment** surface that binds catalog validators to a type's `category`
default bundle plus its own per-type additions. This is EPIC-540's payoff: the
engine FEAT-567 stands up starts actually enforcing something.

## Scope

- **The seed catalog**, lifted 1:1 from today's hardcoded checks (no behaviour
  change except the two deliberate new enforcements below): `parent_in:<types>`,
  `no_parent`, `item_status_valid`, `subtask_story_mapping`,
  `subentity_status_valid`, `subentity_body_written`, `subentity_title_max:<n>`,
  `no_status_banner`, `dangling_ref`, `ref_kind_valid`, `agent_registered`,
  `supersedes_incoming` (per-item class) plus `backend_reconciled` /
  `index_reconciled` (squad-global class, always-on, never per-type selectable).
- **Category default bundles**, implemented as validator-list membership, not a
  parallel mechanism: `records` = common core + `no_parent` +
  `supersedes_incoming` (gated on the type declaring a `supersedes` ref rule);
  `work` = common core + parent validator (per the empty-`parents`/`no_parent`
  semantics ADR-541 pins) + sub-entity validators + `subtask_story_mapping`;
  `roster` = common core only. Common core (all categories): `item_status_valid`,
  `dangling_ref`, `ref_kind_valid`, `no_status_banner`, `agent_registered`.
- **Type-level `validators` list**: extend-only over the category floor (no
  per-validator deselect of a category default — confirmed in ADR-541). A name
  not in the closed catalog fails Plane-1 load validation.
- **The two deliberate new enforcements** ADR-541 calls out: `records`
  category-default `no_parent` (flags the 5 currently-parented ADRs until the
  EPIC-538 migration feature re-homes them — must land with-or-after that
  migration, never before, per ADR-541's sequencing note), and `epic` gaining an
  explicit `no_parent` (enforcing the previously-unenforced work-root
  constraint).
- `parent_in:<types>` requires a **non-empty** allowlist; an empty `parent_in` is
  rejected at Plane 1 load with a diagnostic pointing at `no_parent` instead
  (ADR-541).

## Acceptance

- `sq check` re-expressed entirely over the catalog; a bare `uv run sq check` on
  this repo reports the same issues as today, **except** the two new
  enforcements above (which must be sequenced with the EPIC-538 ADR-migration
  feature so this repo's own `sq check` doesn't regress — see Dependencies).
- create/update and `sq check` share one engine; no rule logic duplicated
  between the abort gate and the report.
- A `validators` entry naming a non-catalog validator fails closed at spec load.
- Category default bundle membership matches ADR-541's bundle table exactly
  (common core + per-category additions).

## Dependencies / ordering

- **Depends on FEAT-567 (Phase A)** — the category axis and the dispatch engine
  must exist before there is anything to populate or assign against.
- **Sequencing constraint with EPIC-538's ADR-migration feature (Phase C)**: the
  `records` `no_parent` default must land with-or-before that migration re-homes
  the 5 currently-parented ADRs (ADR-129/155/158/516/527) to `related` refs —
  landing this enforcement first (without the migration) would make this repo's
  own `sq check` non-clean. Coordinate the merge order with whichever dev picks
  up the migration task.
- Built against ADR-541 (Accepted), Axis B + the seed catalog table.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 568 add-story "As a <role>, I want … so that …"`; track with `sq feature 568 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | lift seed catalog verbatim from today's _check_* methods |
| US2 | Todo |  | category bundles + per-type validators + the two new enforcements |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — lift seed catalog verbatim from today's _check_* methods

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
Named validators 1:1 with today's hardcoded checks, per-item + squad-global classes, byte-identical sq check output for the untouched checks.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — category bundles + per-type validators + the two new enforcements

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
Wire category default bundles, type-level extend-only validators list, records/epic no_parent additions -- sequenced with the ADR-migration feature (Phase C) so this repo's sq check stays clean.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
