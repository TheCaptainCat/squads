---
id: FEAT-567
sequence_id: 567
type: feature
title: Category axis + pluggable-validator dispatch engine
status: Draft
parent: EPIC-538
author: product-owner
priority: high
refs:
- EPIC-540
- ADR-541
subentities:
- local_id: US1
  title: category axis on ItemSpec, replacing is_meta
  status: Todo
- local_id: US2
  title: validator dispatch engine (report + abort modes)
  status: Todo
created_at: '2026-07-22T08:37:44Z'
updated_at: '2026-07-22T08:38:30Z'
---
<!-- sq:body -->
## Capability

The one joint foundation both EPIC-538 and EPIC-540 build on: replace `ItemSpec.is_meta`
with a `category` axis (`roster` / `work` / `records`, hard-coded closed catalog per
ADR-541), and stand up the pluggable-validator dispatch engine that a type's `category`
selects into. Both share one data model — a type's `category` names its behavioural
bundle, and that same bundle is what the validator engine dispatches on. This feature
lands the axis + the engine only; **no enforcement is wired yet** (no `no_parent` on
records, no consumer-site rewiring) — that is Phase B (EPIC-540 catalog + assignment)
and Phase C (EPIC-538 fan-out), both of which depend on this landing first.

## Why

Per ADR-541 (Accepted): `is_meta` conflates "roster vs not" with "burn-down work vs
not", and the current validator set is ~10 hardcoded `_check_*` methods with no
per-type composability. Both problems are fixed by the same underlying move — give
each type a `category`, and let category (+ per-type additions) select which
validators run. Cutting them as one feature keeps the shared data model from forking
into two designs that have to be reconciled later.

## Scope

- `ItemSpec.category: Literal["roster", "work", "records"]` replacing `is_meta: bool`.
  Closed catalog, hard-coded in squads, not on the override surface (ADR-541 Axis A).
  Settled assignments: roster = role/skill/operator (locked, no override may touch
  a roster-category type at all); work = epic/feature/task/bug/review; records =
  decision/contract/guide.
- Plane-1 (load-time) validation: category-catalog membership, roster-locked check
  (no add/deactivate/field-merge/rename touching a `category = roster` type), and
  well-formedness of any category reassignment among `work`/`records` (never into or
  out of `roster`). Fails closed via `SquadsError`, per `load_workflow_spec`.
- The validator **dispatch engine**: one engine, two call sites (report mode for
  `sq check`, abort-on-first-violation mode for create/update) per ADR-541 Axis B.
  Engine takes an item + its type's effective validator set and runs them AND-composed.
  This feature does **not** populate the catalog (Phase B) or point any category's
  bundle at real validators yet — the engine exists and is wired to run an (initially
  empty or stub) per-type validator list, proving the dispatch shape works end to end.
- Rides the `RequestContext` seam FEAT-533 just landed: the active spec (carrying each
  type's `category`) is a per-request value, not a module singleton — this feature adds
  the `category` field onto that per-request spec object, it does not reintroduce a
  global.

## Acceptance

- `ItemSpec.category` exists, is populated for all built-in types per ADR-541's
  settled assignments, and `is_meta` is gone (or a deprecated pure-derived shim, if the
  architect judges a transitional read-compat shim is warranted — see open question).
- A spec with a `category` naming something outside the closed catalog fails to load
  (`SquadsError`), and any override attempting to add/deactivate/field-merge/rename a
  `category = roster` type is refused clean, both at Plane 1 (load).
- The validator engine runs in both report mode and abort mode over a stub/empty
  validator set with no behaviour change to `sq check` output yet (Phase B wires real
  validators — this phase must not regress today's hardcoded `_check_*` results).
- `uv run pytest` green, `sq check` clean, byte-identical `sq check` output vs. today
  (this phase adds no new enforcement).

## Dependencies / ordering

- **Phase A of a A→B→C sequence** (tech-lead's cut): B (EPIC-540 catalog + `.overrides`
  assignment surface) and C (EPIC-538's fan-out: custom types, UI surfacing, CLI
  surfacing, ADR migration, consumer audit) both depend on this landing first. B and C
  do not depend on each other and can run in parallel once A is Done.
- Built against ADR-541 (Accepted) — the category taxonomy and validator-model
  contract are pinned there; this feature does not reopen those questions.
- Rides FEAT-533 (InReview) — the per-request `RequestContext`/active-spec seam.

## Open question — flag @architect

ADR-541 pins the *taxonomy and behavioural contract* but this feature is the first
place the category axis and the validator-engine *code* actually meet — the technical
boundary between "type declares a category" (a spec/model concern) and "engine
dispatches validators by category" (a services-layer concern) isn't fully specified.
Concretely: does the engine live in `_models/` (next to `ItemSpec`) or in `_services/`
(next to `_maintenance.py`'s current `_check_*` methods), and does `ItemSpec` carry a
resolved validator list or just the bare `category` name with resolution happening at
call time in the service layer? This is an architecture call, not a product one —
@architect please pin the module boundary before implementation starts.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 567 add-story "As a <role>, I want … so that …"`; track with `sq feature 567 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | category axis on ItemSpec, replacing is_meta |
| US2 | Todo |  | validator dispatch engine (report + abort modes) |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — category axis on ItemSpec, replacing is_meta

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
Add ItemSpec.category (roster/work/records), settled assignments per ADR-541, drop is_meta, Plane-1 load validation (catalog membership, roster-locked, reassignment well-formedness).
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — validator dispatch engine (report + abort modes)

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
One engine over a per-type validator set, run in sq check report mode and create/update abort mode; no catalog population yet (Phase B), no behaviour change to today's sq check output.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
